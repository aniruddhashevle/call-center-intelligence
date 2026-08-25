import logging
import traceback

logger = logging.getLogger(__name__)

from dataclasses import dataclass
from pathlib import Path
import tempfile


import numpy as np
import soundfile as sf

from src.graph.state import AudioInput, CallReport
from src.graph.workflow import workflow
from src.utils.formatters import format_qa, format_summary, secs_to_mmss
from src.agents.report import generate_report_json, generate_report_pdf


_TEMP_FILES: list[Path] = []
_MAX_TEMP_FILES = 50


@dataclass
class PipelineResult:
    """User-facing result produced by the call-processing pipeline."""

    call_id: str
    status: str
    transcript: str
    summary: str
    qa: str
    pdf_path: str | None = None
    json_path: str | None = None
    report: CallReport | None = None
    error: str | None = None


def _track_temp_file(path: str | Path) -> Path:
    """Track a temporary file and enforce the rolling 50-file limit."""

    file_path = Path(path)
    _TEMP_FILES.append(file_path)

    while len(_TEMP_FILES) > _MAX_TEMP_FILES:
        old_path = _TEMP_FILES.pop(0)

        try:
            old_path.unlink(missing_ok=True)
        except OSError:
            pass

    return file_path


def _write_audio_to_temp(
    audio: tuple[int, np.ndarray],
) -> Path:
    """Write a Gradio (sample_rate, numpy_array) audio tuple to WAV."""

    sample_rate, audio_array = audio

    if audio_array is None:
        raise ValueError("No audio data was provided.")

    audio_array = np.asarray(audio_array)

    if audio_array.size == 0:
        raise ValueError("The uploaded audio is empty.")

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False,
    )

    temp_path = Path(temp_file.name)
    temp_file.close()

    sf.write(
        temp_path,
        audio_array,
        sample_rate,
        format="WAV",
    )

    return _track_temp_file(temp_path)


def _format_transcript(report: CallReport) -> str:
    """Format transcription segments for the Analyze Call UI."""

    transcription = report.transcription

    if transcription is None:
        return ""

    if not transcription.segments:
        if not transcription.text:
            return ""

        return f"[00:00] Speaker: {transcription.text}"

    lines: list[str] = []

    for segment in transcription.segments:
        timestamp = secs_to_mmss(segment.start)
        speaker = segment.speaker or "Speaker"

        low_confidence = (
            " [LOW CONF]"
            if segment.confidence < 0.5
            else ""
        )

        lines.append(
            f"[{timestamp}] "
            f"{speaker}: "
            f"{segment.text}"
            f"{low_confidence}"
        )

    return "\n".join(lines)


def _write_report_files(report: CallReport) -> tuple[str, str]:
    """Write PDF and JSON report files to tracked temporary files."""

    pdf_bytes = generate_report_pdf(report)
    json_text = generate_report_json(report)

    pdf_file = tempfile.NamedTemporaryFile(
        suffix=".pdf",
        delete=False,
    )
    pdf_path = Path(pdf_file.name)

    try:
        pdf_file.write(pdf_bytes)
    finally:
        pdf_file.close()

    json_file = tempfile.NamedTemporaryFile(
        suffix=".json",
        mode="w",
        encoding="utf-8",
        delete=False,
    )
    json_path = Path(json_file.name)

    try:
        json_file.write(json_text)
    finally:
        json_file.close()

    _track_temp_file(pdf_path)
    _track_temp_file(json_path)

    return str(pdf_path), str(json_path)


def process_call(
    audio: tuple[int, np.ndarray] | None,
    caller_id: str | None = None,
    department: str | None = None,
) -> PipelineResult:
    """
    Process a Gradio audio input through the complete pipeline.

    Gradio supplies audio as:
        (sample_rate, numpy_array)
    """

    if audio is None:
        return PipelineResult(
            call_id="",
            status="failed",
            transcript="",
            summary="",
            qa="",
            error="Please upload or record an audio call.",
        )

    try:
        temp_audio_path = _write_audio_to_temp(audio)

        audio_input = AudioInput(
            audio_data=temp_audio_path.read_bytes(),
            filename=temp_audio_path.name,
            caller_id=caller_id or None,
            department=department or None,
        )

        result = workflow.invoke(
            {
                "audio_input": audio_input,
            }
        )

        print("\n=== WORKFLOW RESULT ===")
        print("status:", result.get("status"))
        print("error:", repr(result.get("error")))
        print("keys:", list(result.keys()))
        print("=======================\n")

        status = result.get("status", "failed")

        if status != "completed":
            logger.error(
                "Pipeline failed. status=%r error=%r state_keys=%r",
                status,
                result.get("error"),
                list(result.keys()),
            )

            return PipelineResult(
                call_id=(
                    result.get("intake").call_id
                    if result.get("intake")
                    else ""
                ),
                status=status,
                transcript="",
                summary="",
                qa="",
                error=result.get(
                    "error",
                    "Pipeline processing failed.",
                ),
            )

        report = result["report"]

        transcript_text = _format_transcript(report)
        summary_text = format_summary(report.summary)
        qa_text = format_qa(report.qa_scores)

        pdf_path, json_path = _write_report_files(report)

        return PipelineResult(
            call_id=report.call_id,
            status="completed",
            transcript=transcript_text,
            summary=summary_text,
            qa=qa_text,
            pdf_path=pdf_path,
            json_path=json_path,
            report=report,
        )

    except Exception as exc:
        logger.exception("Pipeline crashed")
        return PipelineResult(
            call_id="",
            status="failed",
            transcript="",
            summary="",
            qa="",
            error=str(exc),
        )