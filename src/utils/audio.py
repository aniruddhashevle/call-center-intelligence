from dataclasses import dataclass
from pathlib import Path
import wave

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4


MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
MAX_DURATION_SECONDS = 3600
SUPPORTED_FORMATS = {"wav", "mp3", "flac", "m4a"}


@dataclass
class ValidationResult:
    is_valid: bool
    error: str | None = None


class AudioValidationError(Exception):
    """Raised when an audio file is corrupt or cannot be read."""

    pass


def detect_audio_format(file_path: str | Path) -> str:
    """
    Detect an audio format using only the first 12 bytes of the file.

    Returns:
        "wav", "mp3", "flac", or "m4a"

    Raises:
        ValueError: If the audio format cannot be identified.
        OSError: If the file cannot be opened/read.
    """
    with open(file_path, "rb") as audio_file:
        header = audio_file.read(12)

    # WAV: "RIFF" at bytes 0-3 and "WAVE" at bytes 8-11.
    if (
        len(header) >= 12
        and header[:4] == b"RIFF"
        and header[8:12] == b"WAVE"
    ):
        return "wav"

    # MP3: ID3 tag.
    if header[:3] == b"ID3":
        return "mp3"

    # MP3: MPEG audio frame sync bits.
    if (
        len(header) >= 2
        and header[0] == 0xFF
        and (header[1] & 0xE0) == 0xE0
    ):
        return "mp3"

    # FLAC: "fLaC" at bytes 0-3.
    if header[:4] == b"fLaC":
        return "flac"

    # M4A/MP4 container: "ftyp" at bytes 4-7.
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return "m4a"

    raise ValueError("Unsupported or unrecognized audio format")


def validate_audio_file(file_path: str | Path) -> ValidationResult:
    """
    Validate an audio file for size and supported format.

    Rejects files that are:
    - Empty
    - Larger than 50 MB
    - In an unsupported or unrecognized format
    """
    path = Path(file_path)

    try:
        file_size = path.stat().st_size
    except OSError as exc:
        return ValidationResult(
            is_valid=False,
            error=f"Unable to access file: {exc}",
        )

    if file_size == 0:
        return ValidationResult(
            is_valid=False,
            error="File is empty.",
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        max_size_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)

        return ValidationResult(
            is_valid=False,
            error=f"File exceeds maximum allowed size of {max_size_mb:g} MB.",
        )

    try:
        audio_format = detect_audio_format(path)
    except (OSError, ValueError) as exc:
        return ValidationResult(
            is_valid=False,
            error=str(exc),
        )

    if audio_format not in SUPPORTED_FORMATS:
        return ValidationResult(
            is_valid=False,
            error=f"Unsupported audio format: {audio_format}",
        )

    return ValidationResult(is_valid=True)


def extract_audio_properties(file_path: str | Path) -> dict:
    """
    Extract audio properties from a supported audio file.

    Returns:
        Dictionary containing:
        - format
        - frame_count
        - sample_rate
        - channel_count

    Raises:
        AudioValidationError: If the file is corrupt, unreadable,
        or has an unsupported format.
    """
    path = Path(file_path)

    try:
        audio_format = detect_audio_format(path)

        if audio_format == "wav":
            with wave.open(str(path), "rb") as audio_file:
                return {
                    "format": "wav",
                    "frame_count": audio_file.getnframes(),
                    "sample_rate": audio_file.getframerate(),
                    "channel_count": audio_file.getnchannels(),
                }

        if audio_format == "mp3":
            audio_file = MP3(path)

            return {
                "format": "mp3",
                "frame_count": int(
                    audio_file.info.length * audio_file.info.sample_rate
                ),
                "sample_rate": audio_file.info.sample_rate,
                "channel_count": audio_file.info.channels,
            }

        if audio_format == "flac":
            audio_file = FLAC(path)

            return {
                "format": "flac",
                "frame_count": audio_file.info.total_samples,
                "sample_rate": audio_file.info.sample_rate,
                "channel_count": audio_file.info.channels,
            }

        if audio_format == "m4a":
            audio_file = MP4(path)

            return {
                "format": "m4a",
                "frame_count": int(
                    audio_file.info.length * audio_file.info.sample_rate
                ),
                "sample_rate": audio_file.info.sample_rate,
                "channel_count": audio_file.info.channels,
            }

        raise AudioValidationError(
            f"Unsupported audio format: {audio_format}"
        )

    except AudioValidationError:
        raise
    except (OSError, ValueError, TypeError, KeyError, EOFError) as exc:
        raise AudioValidationError(
            f"Unable to read audio file: {exc}"
        ) from exc
    except Exception as exc:
        raise AudioValidationError(
            f"Corrupt or unreadable audio file: {exc}"
        ) from exc
