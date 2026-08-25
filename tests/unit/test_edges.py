from src.graph.edges import (
    route_after_injection_check,
    route_after_intake,
    route_after_qa,
    route_after_transcription,
)
from src.graph.state import (
    ComplianceFlag,
    IntakeResult,
    QAScoreResult,
)


def test_route_after_intake_valid():
    state = {
        "intake": IntakeResult(
            call_id="call-001",
            validation_passed=True,
            audio_properties={
                "format": "wav",
                "frame_count": 16000,
                "sample_rate": 16000,
                "channel_count": 1,
                "duration_seconds": 1.0,
            },
            pii_scan={},
        )
    }

    assert route_after_intake(state) == "transcribe"


def test_route_after_intake_invalid():
    state = {
        "intake": IntakeResult(
            call_id="call-001",
            validation_passed=False,
            audio_properties={
                "format": "wav",
                "frame_count": 0,
                "sample_rate": 16000,
                "channel_count": 1,
                "duration_seconds": 0.0,
            },
            pii_scan={},
        )
    }

    assert route_after_intake(state) == "error"


def test_route_after_transcription():
    assert route_after_transcription({}) == "injection_check"


def test_route_after_injection_clean():
    assert route_after_injection_check({}) == "pii_redact"


def test_route_after_injection_flagged():
    state = {
        "status": "flagged_for_review",
    }

    assert route_after_injection_check(state) == "error"


def test_route_after_qa_critical():
    state = {
        "qa_scores": QAScoreResult(
            overall_score=3.0,
            dimension_scores=[],
            compliance_flags=[
                ComplianceFlag(
                    name="policy_violation",
                    triggered=True,
                    severity="critical",
                    details="Critical violation",
                )
            ],
        )
    }

    assert route_after_qa(state) == "supervisor_review"


def test_route_after_qa_non_critical():
    state = {
        "qa_scores": QAScoreResult(
            overall_score=4.0,
            dimension_scores=[],
            compliance_flags=[],
        )
    }

    assert route_after_qa(state) == "report"