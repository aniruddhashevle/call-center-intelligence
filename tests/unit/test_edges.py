from src.graph.edges import (
    route_after_injection_check,
    route_after_intake,
    route_after_pii_redaction,
    route_after_qa,
    route_after_transcription,
)
from src.graph.state import (
    ComplianceFlag,
    IntakeResult,
    QAScoreResult,
    TranscriptionResult,
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
    state = {
        "status": "transcribed",
        "transcription": TranscriptionResult(
            call_id="call-001",
            text="Hello, how can I help you?",
            segments=[],
        ),
    }

    assert route_after_transcription(state) == "injection_check"


def test_route_after_transcription_missing_result():
    state = {
        "status": "transcribed",
    }

    assert route_after_transcription(state) == "error"


def test_route_after_transcription_failed():
    state = {
        "status": "failed",
        "transcription": TranscriptionResult(
            call_id="call-001",
            text="Hello",
            segments=[],
        ),
    }

    assert route_after_transcription(state) == "error"


def test_route_after_injection_clean():
    state = {
        "status": "injection_check_passed",
        "transcription": TranscriptionResult(
            call_id="call-001",
            text="Hello, I need help with my account.",
            segments=[],
        ),
    }

    assert route_after_injection_check(state) == "pii_redact"


def test_route_after_injection_missing_transcription():
    state = {
        "status": "injection_check_passed",
    }

    assert route_after_injection_check(state) == "error"


def test_route_after_injection_failed():
    state = {
        "status": "failed",
    }

    assert route_after_injection_check(state) == "error"


def test_route_after_injection_flagged():
    state = {
        "status": "flagged_for_review",
    }

    assert route_after_injection_check(state) == "error"


def test_route_after_pii_redaction_success():
    state = {
        "status": "pii_redacted",
        "transcription": TranscriptionResult(
            call_id="call-001",
            text="Hello, I need help.",
            segments=[],
        ),
    }

    assert route_after_pii_redaction(state) == "summarize_and_qa"


def test_route_after_pii_redaction_missing_transcription():
    state = {
        "status": "pii_redacted",
    }

    assert route_after_pii_redaction(state) == "error"


def test_route_after_pii_redaction_failed():
    state = {
        "status": "failed",
    }

    assert route_after_pii_redaction(state) == "error"


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