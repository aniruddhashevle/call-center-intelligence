from __future__ import annotations

import gradio as gr

from src.services.pipeline import PipelineResult, process_call


def _show_processing_status() -> gr.Markdown:
    return gr.Markdown(
        """
### ⏳ Processing call...

This may take a few minutes depending on the audio length and Whisper model.

**Estimated duration:** approximately 1–3 minutes.

⚠️ **Please do not refresh or close this page while processing.**
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
        "Upload a call recording or record directly from your microphone."
    )

    audio = gr.Audio(
        sources=["upload", "microphone"],
        type="numpy",
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