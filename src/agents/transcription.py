import hashlib
import re
from pathlib import Path
from dataclasses import dataclass
import json

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


def _check_cache(audio_hash: str) -> TranscriptionResult | None:
    """Return cached transcription text if the audio hash exists."""

    with session_scope() as session:
        cached = (
            session.query(TranscriptionCache)
            .filter_by(audio_hash=audio_hash)
            .first()
        )

        if cached is None:
            return None

        # Convert the JSON string stored in SQLite 
        # back into a Python dictionary.
        data = json.loads(cached.transcription_json) 
        # Reconstruct the complete Pydantic model, 
        # ncluding segments, timestamps, speakers, etc. 
        return TranscriptionResult.model_validate(data)

def _save_cache(
    audio_hash: str,
    call_id: str,
    transcription_result: TranscriptionResult,
) -> None:
    """Save a transcription result to the cache."""

    transcription_json = transcription_result.model_dump_json()

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
                transcription_json=transcription_json,
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
    original_file_path: str | Path,
    file_path: str | Path,
    call_id: str,
    model_size: str = "small",
) -> TranscriptionResult:
    """
    Transcribe an audio file using faster-whisper.

    Uses SHA-256 caching to avoid repeated transcription.
    """

    audio_hash = _compute_audio_hash(original_file_path)

    cached = _check_cache(audio_hash)

    if cached is not None:
        return cached.model_copy( update={ "call_id": call_id, } )

    model = _get_whisper_model(model_size)

    segments, info = model.transcribe(
        str(file_path),
        beam_size=5,
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
        call_id=call_id,
        text=full_text,
        segments=result_segments,
        language="en",
        duration_seconds=duration,
    )

    _save_cache(
        audio_hash=audio_hash,
        call_id=call_id,
        transcription_result=result,
    )

    return result


_AGENT_PATTERNS = [
    re.compile(
    r"\b("
    r"thank you for calling|"
    r"how can I help|"
    r"how may I help|"
    r"let me check|"
    r"let me look|"
    r"I can help you|"
    r"I'll help you|"
    r"I'd be happy to help|"
    r"your account|"
    r"your order|"
    r"please verify|"
    r"can I have your|"
    r"may I have your"
    r")\b",
    re.IGNORECASE,
    ),
]

_CUSTOMER_PATTERNS = [
    re.compile(
    r"\b("
    r"I need help|"
    r"I need|"
    r"I want|"
    r"I'd like|"
    r"my problem|"
    r"my issue|"
    r"I was charged|"
    r"I can't|"
    r"I cannot|"
    r"I was calling|"
    r"I'm calling|"
    r"can you help me"
    r")\b",
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
    """
    Estimate Agent/Customer roles from transcript turn-taking.

    This is heuristic role estimation, not true acoustic speaker
    diarization. Established speakers are preserved unless there is
    meaningful evidence that a conversational turn occurred.
    """

    GAP_THRESHOLD = 1.2
    STRONG_GAP_THRESHOLD = 2.5
    SHORT_SEGMENT_WORDS = 3
    LONG_SEGMENT_WORDS = 8

    def diarize(self, segments) -> list[SpeakerSegment]:
        results: list[SpeakerSegment] = []
        previous: SpeakerSegment | None = None

        for segment in segments:
            text = segment.text.strip()

            if not text:
                continue

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
        agent_match = any(
            pattern.search(text)
            for pattern in _AGENT_PATTERNS
        )

        customer_match = any(
            pattern.search(text)
            for pattern in _CUSTOMER_PATTERNS
        )

        # First segment:
        # use explicit role evidence when available, otherwise assume
        # the call starts with the agent.
        if previous is None:
            if customer_match and not agent_match:
                return "Customer"

            return "Agent"

        previous_speaker = previous.speaker

        opposite_speaker = (
            "Customer"
            if previous_speaker == "Agent"
            else "Agent"
        )

        gap = max(
            0.0,
            current_start - previous.end,
        )

        current_word_count = len(text.split())
        previous_word_count = len(previous.text.split())

        switch_score = 0

        # ---------------------------------------------------------
        # Turn-taking evidence
        # ---------------------------------------------------------

        # Strong pause.
        if gap >= self.STRONG_GAP_THRESHOLD:
            switch_score += 2

        # Normal conversational pause.
        elif gap >= self.GAP_THRESHOLD:
            switch_score += 1

        # Question → response.
        if previous.text.rstrip().endswith("?"):
            switch_score += 2

        # ---------------------------------------------------------
        # Short acknowledgement handling
        # ---------------------------------------------------------

        acknowledgements = {
            "okay",
            "ok",
            "alright",
            "all right",
            "yes",
            "yeah",
            "yep",
            "sure",
            "right",
            "no",
        }

        normalized_text = re.sub(
            r"[.!?,]+$",
            "",
            text.lower(),
        ).strip()

        is_acknowledgement = normalized_text in acknowledgements

        # A short acknowledgement after a substantial statement is
        # strong evidence that the other person has taken the turn.
        if (
            is_acknowledgement
            and previous_word_count >= self.LONG_SEGMENT_WORDS
        ):
            switch_score += 2

        # Generic short segment after a long statement.
        elif (
            current_word_count <= self.SHORT_SEGMENT_WORDS
            and previous_word_count >= self.LONG_SEGMENT_WORDS
        ):
            switch_score += 1

        # ---------------------------------------------------------
        # Content evidence
        # ---------------------------------------------------------
        #
        # Content alone is NOT enough to change an established
        # speaker. It only adds evidence when a turn is already
        # suspected.
        #

        if previous_speaker == "Agent":
            if customer_match and not agent_match:
                switch_score += 2

        else:
            if agent_match and not customer_match:
                switch_score += 2

        # Strongly contradictory content can reinforce an existing
        # turn, but never causes an immediate flip by itself.
        # if previous_speaker == "Agent":
        #     if agent_match and not customer_match:
        #         switch_score = max(0, switch_score - 1)

        # else:
        #     if customer_match and not agent_match:
        #         switch_score = max(0, switch_score - 1)

        # Require meaningful evidence before switching.
        if switch_score >= 2:
            return opposite_speaker

        return previous_speaker