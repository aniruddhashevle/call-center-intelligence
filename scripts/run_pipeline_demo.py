import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import io
import wave
from unittest.mock import patch


from src.graph.state import (
    AudioInput,
    QADimensionScore,
    QAScoreResult,
    ResolutionStatus,
    SummaryResult,
    TranscriptionResult,
)
from src.graph.workflow import workflow


def make_wav_bytes() -> bytes:
    """Create a minimal valid 1-second WAV file."""
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 16000)

    return buffer.getvalue()


def make_summary(call_id: str) -> SummaryResult:
    return SummaryResult(
        call_id=call_id,
        summary="Customer requested help with their account.",
        key_points=[
            "Customer needs account assistance."
        ],
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


def main() -> None:
    print()
    print("=" * 60)
    print("CALL CENTER INTELLIGENCE PIPELINE")
    print("=" * 60)

    audio_input = AudioInput(
        audio_data=make_wav_bytes(),
        filename="demo-call.wav",
    )

    # We don't want this demo to call real Whisper/LLM APIs yet.
    # Instead, mock the expensive external dependencies while
    # running the actual compiled LangGraph workflow.
    transcription_call_id = "demo-call-001"

    transcription = TranscriptionResult(
        call_id=transcription_call_id,
        text="Hello, I need help with my account.",
        segments=[],
        language="en",
        duration_seconds=1.0,
    )

    summary = make_summary(transcription_call_id)
    qa = make_qa()

    print("\nStarting workflow...\n")

    with (
        patch(
            "src.graph.workflow.transcribe_audio",
            return_value=transcription,
        ),
        patch(
            "src.graph.workflow.summarize_transcript",
            return_value=summary,
        ),
        patch(
            "src.graph.workflow.score_call",
            return_value=qa,
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

    print("Pipeline finished.")
    print()

    if result["status"] != "completed":
        print("❌ PIPELINE FAILED")
        print(f"Error: {result.get('error')}")
        return

    report = result["report"]

    print("✅ PIPELINE COMPLETED")
    print("-" * 60)

    print(f"Call ID:          {report.call_id}")
    print(f"Status:           {result['status']}")
    print(f"Sentiment:        {report.summary.sentiment}")
    print(
        f"Resolution:       "
        f"{report.summary.resolution_status.value}"
    )
    print(f"Overall QA Score:  {report.qa_scores.overall_score:.1f}/5")
    print()

    print("Summary:")
    print(f"  {report.summary.summary}")
    print()

    print("QA Dimensions:")

    for dimension in report.qa_scores.dimension_scores:
        print(
            f"  {dimension.dimension:25} "
            f"{dimension.score}/5"
        )

    print()

    if report.qa_scores.compliance_flags:
        print("Compliance Flags:")

        for flag in report.qa_scores.compliance_flags:
            print(
                f"  [{flag.severity.upper()}] "
                f"{flag.name}"
            )
    else:
        print("Compliance Flags: none")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()