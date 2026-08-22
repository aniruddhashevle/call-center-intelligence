import io
import re
import tempfile
import uuid
import wave

from src.graph.state import (
    AudioInput,
    AudioProperties,
    IntakeResult,
    PIIScanResult,
)
from src.utils.audio import (
    detect_audio_format,
    extract_audio_properties,
    validate_audio_file,
)


_EMPTY_AUDIO_PROPS = AudioProperties(
    format="",
    frame_count=0,
    sample_rate=0,
    channel_count=0,
    duration_seconds=0.0,
)

_EMPTY_PII = PIIScanResult(
    pii_detected=False,
    affected_fields=[],
)


SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b")
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
PHONE_PATTERN = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?"
    r"(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"
)


def _make_failed_result(
    call_id: str,
    error: str,
    pii_scan: PIIScanResult = _EMPTY_PII,
) -> IntakeResult:
    return IntakeResult(
        call_id=call_id,
        validation_passed=False,
        audio_properties=_EMPTY_AUDIO_PROPS,
        pii_scan=pii_scan,
        temp_file_path=None,
        error=error,
    )


def _scan_metadata(audio_input: AudioInput) -> PIIScanResult:
    affected_fields: list[str] = []

    metadata = {
        "caller_id": audio_input.caller_id,
        "department": audio_input.department,
    }

    patterns = (
        SSN_PATTERN,
        CREDIT_CARD_PATTERN,
        EMAIL_PATTERN,
        PHONE_PATTERN,
    )

    for field_name, value in metadata.items():
        if value and any(pattern.search(value) for pattern in patterns):
            affected_fields.append(field_name)

    return PIIScanResult(
        pii_detected=bool(affected_fields),
        affected_fields=affected_fields,
    )


def _get_wav_properties(audio_data: bytes) -> AudioProperties:
    with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
        channel_count = wav_file.getnchannels()

    duration_seconds = frame_count / sample_rate

    return AudioProperties(
        format="wav",
        frame_count=frame_count,
        sample_rate=sample_rate,
        channel_count=channel_count,
        duration_seconds=duration_seconds,
    )


def run_intake(audio_input: AudioInput) -> IntakeResult:
    call_id = str(uuid.uuid4())
    pii_scan = _scan_metadata(audio_input)

    try:
        audio_format = _detect_format_from_bytes(audio_input.audio_data)

        # WAV duration must be checked before size validation.
        if audio_format == "wav":
            try:
                audio_properties = _get_wav_properties(
                    audio_input.audio_data
                )
            except (OSError, wave.Error, EOFError, ZeroDivisionError) as exc:
                return _make_failed_result(
                    call_id,
                    f"Unable to read WAV audio: {exc}",
                    pii_scan,
                )

            if audio_properties.duration_seconds > 3600:
                return _make_failed_result(
                    call_id,
                    "Audio duration exceeds maximum of 60 minutes.",
                    pii_scan,
                )

        suffix = f".{audio_format}"

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_file.write(audio_input.audio_data)
            temp_file_path = temp_file.name

        validation = validate_audio_file(temp_file_path)

        if not validation.is_valid:
            return _make_failed_result(
                call_id,
                validation.error or "Audio validation failed.",
                pii_scan,
            )

        # Use the existing Phase 1 property extraction.
        properties = extract_audio_properties(temp_file_path)

        properties["duration_seconds"] = (
            properties["frame_count"] / properties["sample_rate"]
            if properties["sample_rate"]
            else 0.0
        )

        audio_properties = AudioProperties(**properties)

        return IntakeResult(
            call_id=call_id,
            validation_passed=True,
            audio_properties=audio_properties,
            pii_scan=pii_scan,
            temp_file_path=temp_file_path,
            error=None,
        )

    except (OSError, ValueError, RuntimeError) as exc:
        return _make_failed_result(
            call_id,
            str(exc),
            pii_scan,
        )


def _detect_format_from_bytes(audio_data: bytes) -> str:
    header = audio_data[:12]

    if (
        len(header) >= 12
        and header[:4] == b"RIFF"
        and header[8:12] == b"WAVE"
    ):
        return "wav"

    if header[:3] == b"ID3":
        return "mp3"

    if (
        len(header) >= 2
        and header[0] == 0xFF
        and (header[1] & 0xE0) == 0xE0
    ):
        return "mp3"

    if header[:4] == b"fLaC":
        return "flac"

    if len(header) >= 8 and header[4:8] == b"ftyp":
        return "m4a"

    raise ValueError("Unsupported or unrecognized audio format")