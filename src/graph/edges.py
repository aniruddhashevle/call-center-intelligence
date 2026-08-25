from src.graph.state import PipelineState


def route_after_intake(state: PipelineState) -> str:
    """
    Route to transcription when intake succeeds,
    otherwise route to the error handler.
    """
    intake = state.get("intake")

    if intake and intake.validation_passed:
        return "transcribe"

    return "error"


def route_after_transcription(state: PipelineState) -> str:
    """
    Continue only when transcription succeeded.
    """
    if (
        state.get("status") == "transcribed"
        and state.get("transcription") is not None
    ):
        return "injection_check"

    return "error"


def route_after_injection_check(state: PipelineState) -> str:
    """
    Continue only when injection checking succeeded.
    Otherwise stop at the error handler.
    """
    if state.get("status") == "flagged_for_review":
        return "error"

    if (
        state.get("status") == "injection_check_passed"
        and state.get("transcription") is not None
    ):
        return "pii_redact"

    return "error"

# def route_after_injection_check(state: PipelineState) -> str:
#     """
#     Stop processing when prompt injection is detected.
#     Otherwise continue to PII redaction.
#     """
#     if state.get("status") == "flagged_for_review":
#         return "error"

#     return "pii_redact"


def route_after_qa(state: PipelineState) -> str:
    """
    Route critical compliance cases to supervisor review.
    Otherwise proceed to report generation.
    """
    qa_scores = state.get("qa_scores")

    if not qa_scores:
        return "error"

    for flag in qa_scores.compliance_flags:
        if (
            getattr(flag, "triggered", False)
            and getattr(flag, "severity", None) == "critical"
        ):
            return "supervisor_review"

    return "report"


def route_after_pii_redaction(state: PipelineState) -> str:
    """
    Continue to analysis only when PII redaction succeeded.
    """
    if (
        state.get("status") == "pii_redacted"
        and state.get("transcription") is not None
    ):
        return "summarize_and_qa"

    return "error"
