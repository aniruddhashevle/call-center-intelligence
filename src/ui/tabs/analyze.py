from __future__ import annotations
from email.mime import audio
from pathlib import Path

import gradio as gr

from src.services.pipeline import PipelineResult, process_call
from src.utils.audio import validate_audio_file


def _show_processing_status() -> gr.Markdown:
    return gr.Markdown(
        """
### ⏳ Processing call...

This may take a few minutes depending on the audio length and Whisper model.

The processing required few minutes.

⚠️ **Please do not REFRESH or CLOSE this page while processing.**
""",
        visible=True,
    )


def _hide_processing_status() -> gr.Markdown:
    return gr.Markdown(
        "",
        visible=False,
    )

def _process_call(
    audio,
    caller_id,
    department,
    ):
    print("=== PROCESS CALL TRIGGERED ===")
    print("audio type:", type(audio))
    print("audio:", audio)

    if not audio:
        error = "Please upload an audio call."

        result = PipelineResult(
            call_id="",
            status="failed",
            transcript="",
            summary="",
            qa="",
            error=error,
        )

        return (
            result,
            "",
            f"❌ {error}",
            "",
            None,
            None,
        )

    try:
        # Validate the ORIGINAL uploaded file.
        validation = validate_audio_file(Path(audio))

        if not validation.is_valid:
            error = validation.error or "Audio validation failed."

            result = PipelineResult(
                call_id="",
                status="failed",
                transcript="",
                summary="",
                qa="",
                error=error,
            )

            return (
                result,
                "",
                f"❌ {error}",
                "",
                None,
                None,
            )

    except Exception as exc:
        error = str(exc)

        result = PipelineResult(
            call_id="",
            status="failed",
            transcript="",
            summary="",
            qa="",
            error=error,
        )

        return (
            result,
            "",
            f"❌ {error}",
            "",
            None,
            None,
        )

    # Process only once.
    result: PipelineResult = process_call(
        audio=audio,
        caller_id=caller_id or None,
        department=department or None,
    )

    if result.status != "completed":
        return (
            result,
            result.transcript,
            result.summary or f"❌ Pipeline failed: {result.error}",
            result.qa,
            None,
            None,
        )

    return (
        result,
        result.transcript,
        result.summary,
        result.qa,
        result.pdf_path,
        result.json_path,
    )


def build_analyze_tab() -> None:
    """Build the Analyze Call tab."""

    gr.Markdown(
        "# Analyze Call"
    )

    gr.Markdown(
        "Upload a call recording." #TODO: [ENHANCEMENT] record directly from your microphone
    )

    audio = gr.Audio(
        sources=["upload"], #TODO: [ENHANCEMENT] add "microphone" source for direct recording.
        type="filepath",
        label="Call Audio",
    )

    with gr.Row():
        caller_id = gr.Textbox(
            label="Caller ID (optional)",
            placeholder="Enter caller ID",
        )

        department = gr.Textbox(
            label="Department (optional)",
            placeholder="e.g. Billing, Support",
        )

    analyze_button = gr.Button(
        "Analyze Call",
        variant="primary",
    )

    status = gr.Markdown(
        "",
        visible=False,
    )

    transcript = gr.Textbox(
        label="Transcript",
        lines=15,
        buttons=["copy"],
        interactive=False,
    )

    with gr.Row():
        with gr.Column():
            gr.Markdown("## Summary")
            summary = gr.Markdown()

        with gr.Column():
            gr.Markdown("## QA")
            qa = gr.Markdown()

    with gr.Row():
        pdf_file = gr.File(
            label="Download PDF Report",
        )

        json_file = gr.File(
            label="Download JSON Report",
        )

    result_state = gr.State()

    analyze_button.click(
        fn=_show_processing_status,
        inputs=None,
        outputs=status,
    ).then(
        fn=_process_call,
        inputs=[
            audio,
            caller_id,
            department,
        ],
        outputs=[
            result_state,
            transcript,
            summary,
            qa,
            pdf_file,
            json_file,
        ],
    ).then(
        fn=_hide_processing_status,
        inputs=None,
        outputs=status,
    )