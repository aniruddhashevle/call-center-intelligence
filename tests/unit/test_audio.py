import struct
import wave

import pytest

from src.utils.audio import (
    MAX_FILE_SIZE_BYTES,
    AudioValidationError,
    detect_audio_format,
    extract_audio_properties,
    validate_audio_file,
)


def create_file(tmp_path, filename, content):
    file_path = tmp_path / filename
    file_path.write_bytes(content)
    return file_path


def create_wav_file(
    tmp_path,
    filename="test.wav",
    sample_rate=16000,
    channels=1,
    duration_seconds=2,
):
    file_path = tmp_path / filename

    sample_width = 2
    frame_count = sample_rate * duration_seconds

    audio_data = b"\x00" * (
        frame_count * channels * sample_width
    )

    with wave.open(str(file_path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)

    return file_path


def test_detect_wav_format(tmp_path):
    file_path = create_file(
        tmp_path,
        "audio.bin",
        b"RIFF" + struct.pack("<I", 36) + b"WAVE" + b"\x00" * 100,
    )

    assert detect_audio_format(file_path) == "wav"


def test_detect_mp3_format_with_id3_header(tmp_path):
    file_path = create_file(
        tmp_path,
        "audio.bin",
        b"ID3" + b"\x00" * 100,
    )

    assert detect_audio_format(file_path) == "mp3"


def test_detect_flac_format(tmp_path):
    file_path = create_file(
        tmp_path,
        "audio.bin",
        b"fLaC" + b"\x00" * 100,
    )

    assert detect_audio_format(file_path) == "flac"


def test_detect_m4a_format(tmp_path):
    file_path = create_file(
        tmp_path,
        "audio.bin",
        b"\x00\x00\x00\x18ftyp" + b"\x00" * 100,
    )

    assert detect_audio_format(file_path) == "m4a"


def test_reject_unsupported_ogg_format(tmp_path):
    file_path = create_file(
        tmp_path,
        "audio.ogg",
        b"OggS" + b"\x00" * 100,
    )

    with pytest.raises(ValueError, match="Unsupported or unrecognized"):
        detect_audio_format(file_path)


def test_validate_empty_file(tmp_path):
    file_path = create_file(
        tmp_path,
        "empty.wav",
        b"",
    )

    result = validate_audio_file(file_path)

    assert result.is_valid is False
    assert result.error == "File is empty."


def test_validate_file_over_50_mb(tmp_path):
    file_path = tmp_path / "large.wav"

    with file_path.open("wb") as audio_file:
        audio_file.truncate(MAX_FILE_SIZE_BYTES + 1)

    result = validate_audio_file(file_path)

    assert result.is_valid is False
    assert result.error == "File is larger than 50 MB."


def test_extract_wav_properties(tmp_path):
    sample_rate = 16000
    channels = 2
    duration_seconds = 3

    file_path = create_wav_file(
        tmp_path,
        sample_rate=sample_rate,
        channels=channels,
        duration_seconds=duration_seconds,
    )

    properties = extract_audio_properties(file_path)

    assert properties["format"] == "wav"
    assert properties["sample_rate"] == sample_rate
    assert properties["channel_count"] == channels

    expected_frame_count = sample_rate * duration_seconds
    assert properties["frame_count"] == expected_frame_count

    actual_duration = (
        properties["frame_count"] / properties["sample_rate"]
    )

    assert actual_duration == duration_seconds


def test_extract_properties_from_corrupt_wav(tmp_path):
    file_path = create_file(
        tmp_path,
        "corrupt.wav",
        b"RIFF" + b"\x00" * 20,
    )

    with pytest.raises(AudioValidationError):
        extract_audio_properties(file_path)
