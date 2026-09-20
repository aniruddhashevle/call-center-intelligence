from src.graph.state import PipelineState

def route_after_intake(state: PipelineState) -> str:
    intake = state.get("intake")

    print("DEBUG intake:", intake)
    print(
        "DEBUG validation_passed:",
        getattr(intake, "validation_passed", None),
    )
    print(
        "DEBUG temp_file_path:",
        getattr(intake, "temp_file_path", None),
    )

    if intake is None:
        return "error"

    if intake.validation_passed:
        return "transcribe"

    return "error"

def route_after_transcription(state: PipelineState) -> str:
    """
    Continue to injection checking only when transcription succeeded.
    """
    transcription = state.get("transcription")

    if (
        state.get("status") == "transcribed"
        and transcription is not None
    ):
        return "injection_check"

    return "error"

def route_after_injection_check(state: PipelineState) -> str:
    """
    Stop processing when prompt injection is detected.
    Otherwise continue to PII redaction.
    """
    if state.get("status") == "flagged_for_review":
        return "error"

    if (
        state.get("status") == "injection_check_passed"
        and state.get("transcription") is not None
    ):
        return "pii_redact"

    return "error"

def route_after_pii_redaction(state: PipelineState) -> str:
    """
    Continue to summarization and QA only when PII
    redaction completed successfully.
    """
    if (
    state.get("status") == "pii_redacted"
    and state.get("transcription") is not None
    ):
        return "summarize_and_qa"

    return "error"

def route_after_qa(state: PipelineState) -> str:
    """
    Route critical compliance cases to supervisor review.
    Otherwise proceed to report generation.
    """
    qa_scores = state.get("qa_scores")

    if qa_scores is None:
        return "error"

    for flag in qa_scores.compliance_flags:
        if (
            flag.triggered
            and flag.severity.lower() == "critical"
        ):
            return "supervisor_review"

    return "report"
