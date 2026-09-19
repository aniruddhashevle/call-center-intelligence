from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langsmith import traceable

from src.agents.qa_scoring import score_call
from src.agents.report import compile_report, persist_report
from src.agents.summarization import summarize_transcript
from src.agents.transcription import transcribe_audio
from src.graph.edges import (
    route_after_injection_check,
    route_after_intake,
    route_after_pii_redaction,
    route_after_qa,
    route_after_transcription,
)
from src.graph.state import PIIScanResult, PipelineState
from src.security.injection_detector import detect_prompt_injection
from src.security.pii_redactor import redact_pii
from src.security.pii_redactor import (
    detect_pii,
    redact_pii,
)


@traceable
def intake_step(state: PipelineState) -> PipelineState:
    try:
        audio_input = state["audio_input"]

        from src.agents.intake import run_intake

        result = run_intake(audio_input)

        return {
            **state,
            "intake": result,
            "status": (
                "intake_passed"
                if result.validation_passed
                else "failed"
            ),
        }

    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            "transcription_node failed"
        )

        return {
            **state,
            "status": "failed",
            "error": str(exc),
        }


@traceable
def transcription_node(state: PipelineState) -> PipelineState:
    try:
        intake = state["intake"]

        if not intake.temp_file_path:
            raise ValueError("No temporary audio file available")

        result = transcribe_audio(
            original_file_path=Path(intake.original_file_path),
            file_path=Path(intake.temp_file_path),
            call_id=intake.call_id,
        )

        return {
            **state,
            "transcription": result,
            "status": "transcribed",
        }

    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            "transcription_node failed"
        )

        return {
            **state,
            "status": "failed",
            "error": str(exc),
        }


@traceable
def injection_check_node(state: PipelineState) -> PipelineState:
    try:
        transcription = state.get("transcription")

        if transcription is None:
            raise ValueError(
                "Transcription result is missing before injection check."
            )

        detected_patterns = detect_prompt_injection(
            transcription.text
        )

        if detected_patterns:
            return {
                **state,
                "status": "flagged_for_review",
                "error": (
                    "Prompt injection detected: "
                    + ", ".join(detected_patterns)
                ),
            }

        return {
            **state,
            "status": "injection_check_passed",
        }

    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            "transcription_node failed"
        )

        return {
            **state,
            "status": "failed",
            "error": str(exc),
        }


@traceable
def pii_redaction_node(state: PipelineState) -> PipelineState:
    try:
        transcription = state.get("transcription")

        if transcription is None:
            raise ValueError(
                "Transcription result is missing before PII redaction."
            )

        # Detect PII before modifying the transcript.
        detected_pii = detect_pii(transcription.text)

        # Redact complete transcript.
        redacted_text = redact_pii(transcription.text)

        # Redact each segment individually.
        redacted_segments = []

        for segment in transcription.segments:
            segment_pii = detect_pii(segment.text)

            for pii_type in segment_pii:
                if pii_type not in detected_pii:
                    detected_pii.append(pii_type)

            redacted_segment = segment.model_copy(
                update={
                    "text": redact_pii(segment.text),
                }
            )

            redacted_segments.append(redacted_segment)

        redacted_transcription = transcription.model_copy(
            update={
                "text": redacted_text,
                "segments": redacted_segments,
            }
        )

        # Merge transcript PII with any PII already detected during intake.
        intake = state.get("intake")

        if intake is not None:
            existing_fields = list(
                intake.pii_scan.affected_fields
            )

            if detected_pii and "transcript" not in existing_fields:
                existing_fields.append("transcript")

            updated_pii_scan = intake.pii_scan.model_copy(
                update={
                    "pii_detected": bool(
                        existing_fields
                    ),
                    "affected_fields": existing_fields,
                }
            )

            updated_intake = intake.model_copy(
                update={
                    "pii_scan": updated_pii_scan,
                }
            )
        else:
            updated_intake = intake

        return {
            **state,
            "intake": updated_intake,
            "transcription": redacted_transcription,
            "status": "pii_redacted",
        }

    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            "pii_redaction_node failed"
        )

        return {
            **state,
            "status": "failed",
            "error": str(exc),
        }


@traceable
def summarize_and_qa_node(state: PipelineState) -> PipelineState:
    try:
        transcription = state.get("transcription")

        if transcription is None:
            raise ValueError(
                "Transcription result is missing before summarization."
            )

        summary = summarize_transcript(transcription)

        qa_scores = score_call(
            transcript=transcription,
            summary=summary,
        )

        return {
            **state,
            "summary": summary,
            "qa_scores": qa_scores,
            "status": "analyzed",
        }

    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            "transcription_node failed"
        )

        return {
            **state,
            "status": "failed",
            "error": str(exc),
        }


@traceable
def report_node(state: PipelineState) -> PipelineState:
    try:
        report = compile_report(
            call_id=state["intake"].call_id,
            summary=state["summary"],
            qa_scores=state["qa_scores"],
            transcription=state["transcription"],
        )

        persist_report(
            report,
            audio_filename=state["audio_input"].filename,
        )

        return {
            **state,
            "report": report,
            "status": "completed",
        }

    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            "transcription_node failed"
        )

        return {
            **state,
            "status": "failed",
            "error": str(exc),
        }


@traceable
def supervisor_review_node(state: PipelineState) -> PipelineState:
    return {
        **state,
        "status": "supervisor_review",
    }


@traceable
def error_node(state: PipelineState) -> PipelineState:
    return {
        **state,
        "status": "failed",
        "error": state.get("error")
        or (
            state.get("intake").error
            if state.get("intake") is not None
            else None
        ),
    }


def build_workflow():
    graph = StateGraph(PipelineState)

    graph.add_node("intake_step", intake_step)
    graph.add_node("transcription_step", transcription_node)
    graph.add_node("injection_check_step", injection_check_node)
    graph.add_node("pii_redact_step", pii_redaction_node)
    graph.add_node("summarize_and_qa_step", summarize_and_qa_node)
    graph.add_node("report_step", report_node)
    graph.add_node("error_step", error_node)
    graph.add_node("supervisor_review_step", supervisor_review_node)

    graph.add_edge(START, "intake_step")

    graph.add_conditional_edges(
        "intake_step",
        route_after_intake,
        {
            "transcribe": "transcription_step",
            "error": "error_step",
        },
    )

    graph.add_conditional_edges(
        "transcription_step",
        route_after_transcription,
        {
            "injection_check": "injection_check_step",
            "error": "error_step",
        },
    )

    graph.add_conditional_edges(
        "injection_check_step",
        route_after_injection_check,
        {
            "pii_redact": "pii_redact_step",
            "error": "error_step",
        },
    )

    graph.add_conditional_edges(
        "pii_redact_step",
        route_after_pii_redaction,
        {
            "summarize_and_qa": "summarize_and_qa_step",
            "error": "error_step",
        },
    )

    graph.add_conditional_edges(
        "summarize_and_qa_step",
        route_after_qa,
        {
            "report": "report_step",
            "supervisor_review": "supervisor_review_step",
            "error": "error_step",
        },
    )

    graph.add_edge("report_step", END)
    graph.add_edge("supervisor_review_step", END)
    graph.add_edge("error_step", END)

    return graph.compile()


def compile_workflow(config, db_engine=None):
    return build_workflow()


workflow = build_workflow()

