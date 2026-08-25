from src.agents.report import (
    compile_report,
    generate_report_json,
    generate_report_pdf,
)
from src.graph.state import (
    QADimensionScore,
    QAScoreResult,
    ResolutionStatus,
    SummaryResult,
    TranscriptionResult,
)


def make_summary():
    return SummaryResult(
        call_id="call-report-001",
        summary="Customer requested help with an account.",
        key_points=[
            "Customer needs account assistance."
        ],
        resolution_status=ResolutionStatus.resolved,
        sentiment="neutral",
        action_items=[],
        entities=[],
    )


def make_qa():
    return QAScoreResult(
        overall_score=4.0,
        dimension_scores=[
            QADimensionScore(
                dimension="professionalism",
                score=4,
                justification="Professional handling.",
            ),
        ],
    )


def make_transcription():
    return TranscriptionResult(
        call_id="call-report-001",
        text="Hello, I need help with my account.",
        segments=[],
        language="en",
        duration_seconds=5.0,
    )


def make_report():
    return compile_report(
        call_id="call-report-001",
        summary=make_summary(),
        qa_scores=make_qa(),
        transcription=make_transcription(),
    )


def test_compile_report():
    report = make_report()

    assert report.call_id == "call-report-001"
    assert report.summary.summary == (
        "Customer requested help with an account."
    )
    assert report.qa_scores.overall_score == 4.0
    assert report.transcription is not None


def test_generate_report_json():
    report = make_report()

    result = generate_report_json(report)

    assert isinstance(result, str)
    assert "call-report-001" in result
    assert "Customer requested help" in result


def test_generate_report_pdf():
    report = make_report()

    result = generate_report_pdf(report)

    assert isinstance(result, bytes)
    assert len(result) > 0
    assert result.startswith(b"%PDF")