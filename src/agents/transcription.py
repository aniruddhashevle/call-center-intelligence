import hashlib
import re
from pathlib import Path
from dataclasses import dataclass

from src.database.models import TranscriptionCache
from src.database.session import session_scope
from src.graph.state import (
    AudioProperties,
    TranscriptionResult,
    TranscriptionSegment,
)


_model = None
_model_size = None


def _get_whisper_model(model_size: str):
    """
    Return a singleton faster-whisper model.

    CUDA is used when available.
    Apple Silicon MPS falls back to CPU.
    """
    global _model
    global _model_size

    if _model is not None and _model_size == model_size:
        return _model

    device = "cpu"
    compute_type = "int8"

    try:
        import torch

        if torch.cuda.is_available():
            device = "cuda"
            compute_type = "float16"
    except ImportError:
        pass

    from faster_whisper import WhisperModel

    _model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
    )
    _model_size = model_size

    return _model


def _compute_audio_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash using 8 KB chunks."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as audio_file:
        while chunk := audio_file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def _check_cache(audio_hash: str):
    """Return cached transcription if the audio hash exists."""

    with session_scope() as session:
        cached = (
            session.query(TranscriptionCache)
            .filter_by(audio_hash=audio_hash)
            .first()
        )

        if cached is None:
            return None

        return cached


def _save_cache(
    audio_hash: str,
    transcription: str,
    call_id: str,
) -> None:
    """Save a transcription result to the cache."""

    with session_scope() as session:
        existing = (
            session.query(TranscriptionCache)
            .filter_by(audio_hash=audio_hash)
            .first()
        )

        if existing is not None:
            return

        session.add(
            TranscriptionCache(
                audio_hash=audio_hash,
                transcription=transcription,
                call_id=call_id,
            )
        )


def _clean_transcript_text(text: str) -> str:
    """Remove common Whisper transcription artifacts."""

    # [BLANK_AUDIO]
    text = re.sub(
        r"\[BLANK_AUDIO\]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Four or more dots → three dots.
    text = re.sub(r"\.{4,}", "...", text)

    # YouTube-style footer.
    text = re.sub(
        r"\bthanks for watching\b[.!]*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Non-speech labels.
    text = re.sub(
        r"\b(music|applause)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Collapse repeated phrases.
    # Example:
    # "thank you thank you thank you"
    # → "thank you"
    words = text.split()

    for phrase_length in range(5, 0, -1):
        changed = True

        while changed:
            changed = False
            result = []
            index = 0

            while index < len(words):
                if index + (phrase_length * 3) <= len(words):
                    phrase = words[index:index + phrase_length]

                    second = words[
                        index + phrase_length:
                        index + phrase_length * 2
                    ]

                    third = words[
                        index + phrase_length * 2:
                        index + phrase_length * 3
                    ]

                    if (
                        [word.lower() for word in phrase]
                        == [word.lower() for word in second]
                        == [word.lower() for word in third]
                    ):
                        result.extend(phrase)
                        index += phrase_length * 3
                        changed = True
                        continue

                result.append(words[index])
                index += 1

            words = result

    return " ".join(words).strip()


def _calculate_confidence(segment) -> float:
    """Calculate confidence from log probability and no-speech probability."""

    logprob_conf = max(
        0.0,
        min(1.0, 1.0 + segment.avg_logprob),
    )

    speech_conf = 1.0 - segment.no_speech_prob

    confidence = (
        logprob_conf * 0.7
        + speech_conf * 0.3
    )

    return round(confidence, 4)


def transcribe_audio(
    file_path: str | Path,
    call_id: str,
    model_size: str = "base",
) -> TranscriptionResult:
    """
    Transcribe an audio file using faster-whisper.

    Uses SHA-256 caching to avoid repeated transcription.
    """

    audio_hash = _compute_audio_hash(file_path)

    cached = _check_cache(audio_hash)

    if cached is not None:
        return TranscriptionResult(
            text=cached.transcription,
            segments=[],
            language="en",
            duration_seconds=None,
        )

    model = _get_whisper_model(model_size)

    segments, info = model.transcribe(
        str(file_path),
        beam_size=1,
        language="en",
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 300,
        },
        word_timestamps=True,
        condition_on_previous_text=False,
    )

    result_segments = []

    for segment in segments:
        text = _clean_transcript_text(segment.text)

        if not text:
            continue

        result_segments.append(
            TranscriptionSegment(
                start=segment.start,
                end=segment.end,
                text=text,
                confidence=_calculate_confidence(segment),
            )
        )

    # Assign Agent / Customer labels.
    diarizer = SpeakerDiarizer()
    speaker_segments = diarizer.diarize(result_segments)

    for original, speaker_segment in zip(
        result_segments,
        speaker_segments,
    ):
        original.speaker = speaker_segment.speaker

    full_text = " ".join(
        segment.text for segment in result_segments
    )

    full_text = _clean_transcript_text(full_text)

    duration = getattr(info, "duration", None)

    result = TranscriptionResult(
        text=full_text,
        segments=result_segments,
        language="en",
        duration_seconds=duration,
    )

    _save_cache(
        audio_hash=audio_hash,
        transcription=full_text,
        call_id=call_id,
    )

    return result


_AGENT_PATTERNS = [
    re.compile(
        r"\b(how can I help|how may I help|"
        r"thank you for calling|"
        r"let me check|"
        r"I can help|"
        r"your account|"
        r"your order)\b",
        re.IGNORECASE,
    ),
]

_CUSTOMER_PATTERNS = [
    re.compile(
        r"\b(I need|I want|"
        r"my problem|"
        r"my issue|"
        r"I was charged|"
        r"I can't|"
        r"I cannot|"
        r"can you help)\b",
        re.IGNORECASE,
    ),
]


@dataclass
class SpeakerSegment:
    start: float
    end: float
    text: str
    speaker: str


class SpeakerDiarizer:
    """Assign Agent/Customer labels using transcript context."""

    def diarize(self, segments) -> list[SpeakerSegment]:
        results = []
        previous = None

        for segment in segments:
            text = segment.text.strip()

            speaker = self._classify_segment(
                text=text,
                previous=previous,
                current_start=segment.start,
            )

            result = SpeakerSegment(
                start=segment.start,
                end=segment.end,
                text=text,
                speaker=speaker,
            )

            results.append(result)
            previous = result

        return results

    def _classify_segment(
        self,
        text: str,
        previous: SpeakerSegment | None,
        current_start: float,
    ) -> str:
        # 1. Content patterns have highest priority.
        if any(pattern.search(text) for pattern in _AGENT_PATTERNS):
            return "Agent"

        if any(pattern.search(text) for pattern in _CUSTOMER_PATTERNS):
            return "Customer"

        if previous is None:
            return "Agent"

        # 2. A long gap usually indicates a speaker turn.
        gap = current_start - previous.end

        if gap > 1.2:
            return (
                "Customer"
                if previous.speaker == "Agent"
                else "Agent"
            )

        # 3. Question → answer usually changes speaker.
        if previous.text.rstrip().endswith("?"):
            return (
                "Customer"
                if previous.speaker == "Agent"
                else "Agent"
            )

        # 4. Short affirmation after a long segment.
        word_count = len(text.split())
        previous_word_count = len(previous.text.split())

        if (
            word_count <= 3
            and previous_word_count > 8
        ):
            return (
                "Customer"
                if previous.speaker == "Agent"
                else "Agent"
            )

        # Otherwise keep the previous speaker.
        return previous.speaker