import io
import wave
from unittest.mock import patch

from src.graph.state import (
    AudioInput,
    QADimensionScore,
    QAScoreResult,
    SummaryResult,
    ResolutionStatus,
    TranscriptionResult,
)
from src.graph.workflow import workflow


def make_wav_bytes() -> bytes:
    """Create a minimal valid WAV file for the intake stage."""
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)

        # 1 second of silence.
        wav.writeframes(b"\x00\x00" * 16000)

    return buffer.getvalue()


def make_summary(call_id: str) -> SummaryResult:
    return SummaryResult(
        call_id=call_id,
        summary="Customer requested help with their account.",
        key_points=["Customer needs account assistance."],
        resolution_status=ResolutionStatus.resolved,
        sentiment="neutral",
        action_items=[],
        entities=[],
    )


def make_qa() -> QAScoreResult:
    dimensions = [
        QADimensionScore(
            dimension="professionalism",
            score=4,
            justification="Professional interaction.",
        ),
        QADimensionScore(
            dimension="empathy",
            score=4,
            justification="Acknowledged the customer's concern.",
        ),
        QADimensionScore(
            dimension="problem_resolution",
            score=4,
            justification="Addressed the customer's request.",
        ),
        QADimensionScore(
            dimension="compliance",
            score=4,
            justification="No procedural violations observed.",
        ),
        QADimensionScore(
            dimension="communication_clarity",
            score=4,
            justification="Communication was clear.",
        ),
    ]

    return QAScoreResult(
        overall_score=4.0,
        dimension_scores=dimensions,
        compliance_flags=[],
    )


def test_pipeline_success():
    call_id = "integration-call-001"

    audio_input = AudioInput(
        audio_data=make_wav_bytes(),
        filename="test.wav",
        original_file_path="/home/user/projects/test.wav", # sample path
    )

    transcription = TranscriptionResult(
        call_id=call_id,
        text="Hello, I need help with my account.",
        segments=[],
        language="en",
        duration_seconds=1.0,
    )

    with (
        patch(
            "src.graph.workflow.transcribe_audio",
            return_value=transcription,
        ),
        patch(
            "src.graph.workflow.summarize_transcript",
            return_value=make_summary(call_id),
        ),
        patch(
            "src.graph.workflow.score_call",
            return_value=make_qa(),
        ),
        patch(
            "src.graph.workflow.persist_report",
        ),
    ):
        result = workflow.invoke(
            {
                "audio_input": audio_input,
            }
        )

    assert result["status"] == "completed", result.get("error")
    assert result["report"] is not None
    assert result["report"].call_id == result["intake"].call_id


def test_pipeline_invalid_audio_fails():
    audio_input = AudioInput(
        audio_data=b"not audio",
        filename="invalid.wav",
    )

    result = workflow.invoke(
        {
            "audio_input": audio_input,
        }
    )

    assert result["status"] == "failed"