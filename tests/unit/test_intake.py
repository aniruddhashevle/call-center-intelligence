import io
import wave

from src.agents.intake import run_intake
from src.graph.state import AudioInput


def make_wav_bytes(
    duration_seconds=2,
    sample_rate=16000,
    channels=1,
):
    buffer = io.BytesIO()

    frame_count = int(sample_rate * duration_seconds)
    audio_data = b"\x00" * (frame_count * channels * 2)

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)

    return buffer.getvalue()


def test_valid_wav_intake():
    audio = AudioInput(
        audio_data=make_wav_bytes(),
        filename="call.wav",
    )

    result = run_intake(audio)

    assert result.validation_passed is True
    assert result.error is None
    assert result.audio_properties.format == "wav"
    assert result.audio_properties.sample_rate == 16000
    assert result.audio_properties.channel_count == 1


def test_empty_file_rejected():
    audio = AudioInput(
        audio_data=b"",
        filename="empty.wav",
    )

    result = run_intake(audio)

    assert result.validation_passed is False
    assert result.error is not None


def test_unsupported_format_rejected():
    audio = AudioInput(
        audio_data=b"OggS" + b"\x00" * 100,
        filename="call.ogg",
    )

    result = run_intake(audio)

    assert result.validation_passed is False
    assert "Unsupported" in result.error


def test_wav_over_60_minutes_rejected():
    audio = AudioInput(
        audio_data=make_wav_bytes(
            duration_seconds=3601,
            sample_rate=1,
        ),
        filename="long.wav",
    )

    result = run_intake(audio)

    assert result.validation_passed is False
    assert "duration" in result.error.lower()


def test_pii_in_caller_id():
    audio = AudioInput(
        audio_data=make_wav_bytes(),
        filename="call.wav",
        caller_id="123-45-6789",
    )

    result = run_intake(audio)

    assert result.pii_scan.pii_detected is True
    assert "caller_id" in result.pii_scan.affected_fields


def test_two_calls_generate_different_call_ids():
    audio = AudioInput(
        audio_data=make_wav_bytes(),
        filename="call.wav",
    )

    result_1 = run_intake(audio)
    result_2 = run_intake(audio)

    assert result_1.call_id != result_2.call_id