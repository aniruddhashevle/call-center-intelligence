from types import SimpleNamespace

from src.agents import transcription


class FakeSegment:
    def __init__(
        self,
        text,
        start=0.0,
        end=1.0,
        avg_logprob=-0.2,
        no_speech_prob=0.1,
    ):
        self.text = text
        self.start = start
        self.end = end
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob


class FakeModel:
    def __init__(self, segments):
        self.segments = segments
        self.calls = []

    def transcribe(self, file_path, **kwargs):
        self.calls.append((file_path, kwargs))

        info = SimpleNamespace(
            duration=10.0,
            language="en",
        )

        return iter(self.segments), info


def test_compute_audio_hash(tmp_path):
    file_path = tmp_path / "audio.wav"
    file_path.write_bytes(b"hello audio")

    first_hash = transcription._compute_audio_hash(file_path)
    second_hash = transcription._compute_audio_hash(file_path)

    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_clean_transcript_text():
    text = (
        "[BLANK_AUDIO] "
        "Hello.... "
        "music "
        "thank you thank you thank you "
        "Thanks for watching"
    )

    result = transcription._clean_transcript_text(text)

    assert "[BLANK_AUDIO]" not in result
    assert "music" not in result.lower()
    assert "thanks for watching" not in result.lower()
    assert "thank you thank you thank you" not in result


def test_calculate_confidence():
    segment = FakeSegment(
        text="hello",
        avg_logprob=-0.2,
        no_speech_prob=0.1,
    )

    confidence = transcription._calculate_confidence(segment)

    expected = round(
        (1 - 0.2) * 0.7
        + (1 - 0.1) * 0.3,
        4,
    )

    assert confidence == expected


def test_transcribe_audio_calls_whisper_with_required_options(
    tmp_path,
    monkeypatch,
):
    file_path = tmp_path / "audio.wav"
    file_path.write_bytes(b"fake audio")

    fake_segment = FakeSegment(
        text="Hello customer",
        start=0.0,
        end=2.0,
    )

    fake_model = FakeModel([fake_segment])

    monkeypatch.setattr(
        transcription,
        "_get_whisper_model",
        lambda model_size: fake_model,
    )

    monkeypatch.setattr(
        transcription,
        "_check_cache",
        lambda audio_hash: None,
    )

    saved = {}

    def fake_save_cache(audio_hash, transcription, call_id):
        saved["audio_hash"] = audio_hash
        saved["transcription"] = transcription
        saved["call_id"] = call_id

    monkeypatch.setattr(
        transcription,
        "_save_cache",
        fake_save_cache,
    )

    result = transcription.transcribe_audio(
        file_path,
        call_id="call-123",
        model_size="base",
    )

    assert result.text == "Hello customer"
    assert len(result.segments) == 1
    assert result.segments[0].text == "Hello customer"
    assert result.segments[0].confidence > 0

    assert saved["call_id"] == "call-123"

    _, kwargs = fake_model.calls[0]

    assert kwargs["beam_size"] == 5
    assert kwargs["language"] == "en"
    assert kwargs["vad_filter"] is True
    assert kwargs["vad_parameters"] == {
        "min_silence_duration_ms": 300
    }
    assert kwargs["word_timestamps"] is True
    assert kwargs["condition_on_previous_text"] is False



def test_transcribe_audio_returns_cached_result(
    tmp_path,
    monkeypatch,
):
    file_path = tmp_path / "audio.wav"
    file_path.write_bytes(b"fake audio")

    monkeypatch.setattr(
        transcription,
        "_check_cache",
        lambda audio_hash: "Cached transcript",
    )

    def fail_if_model_called(model_size):
        raise AssertionError(
            "Whisper should not be loaded on cache hit"
        )

    monkeypatch.setattr(
        transcription,
        "_get_whisper_model",
        fail_if_model_called,
    )

    result = transcription.transcribe_audio(
        file_path,
        call_id="new-call",
    )

    assert result.text == "Cached transcript"
    assert result.call_id == "new-call"
    assert result.language == "en"
    assert result.segments == []
    assert result.duration_seconds is None


def test_speaker_diarizer_agent_content_pattern():
    segments = [
        FakeSegment(
            "Thank you for calling, how can I help?",
            start=0.0,
            end=2.0,
        ),
    ]

    diarizer = transcription.SpeakerDiarizer()

    result = diarizer.diarize(segments)

    assert result[0].speaker == "Agent"


def test_speaker_diarizer_customer_content_pattern():
    segments = [
        FakeSegment(
            "My problem is that I was charged twice.",
            start=0.0,
            end=2.0,
        ),
    ]

    diarizer = transcription.SpeakerDiarizer()

    result = diarizer.diarize(segments)

    assert result[0].speaker == "Customer"


def test_speaker_diarizer_switches_after_gap():
    segments = [
        FakeSegment(
            "Thank you for calling.",
            start=0.0,
            end=1.0,
        ),
        FakeSegment(
            "I need help with my account.",
            start=2.5,
            end=4.0,
        ),
    ]

    diarizer = transcription.SpeakerDiarizer()

    result = diarizer.diarize(segments)

    assert result[0].speaker == "Agent"
    assert result[1].speaker == "Customer"


def test_speaker_diarizer_switches_after_question():
    segments = [
        FakeSegment(
            "How can I help you?",
            start=0.0,
            end=2.0,
        ),
        FakeSegment(
            "I need help with my order.",
            start=2.2,
            end=4.0,
        ),
    ]

    diarizer = transcription.SpeakerDiarizer()

    result = diarizer.diarize(segments)

    assert result[0].speaker == "Agent"
    assert result[1].speaker == "Customer"


def test_speaker_diarizer_short_affirmation():
    segments = [
        FakeSegment(
            "I have checked your account and everything "
            "looks correct on our side.",
            start=0.0,
            end=5.0,
        ),
        FakeSegment(
            "Okay.",
            start=5.2,
            end=5.8,
        ),
    ]

    diarizer = transcription.SpeakerDiarizer()

    result = diarizer.diarize(segments)

    assert result[0].speaker == "Agent"
    assert result[1].speaker == "Customer"