from __future__ import annotations

import gradio as gr

from src.services.observability import get_observability_dashboard


def _refresh_dashboard():
    return get_observability_dashboard()


def build_observability_tab(tab) -> None:
    """Build the pipeline observability dashboard."""

    gr.Markdown("# Pipeline Observability")

    metrics = gr.Markdown(
        "Loading pipeline metrics..."
    )

    langsmith = gr.Markdown(
        "Loading LangSmith status..."
    )

    audit_events = gr.Dataframe(
        headers=[
            "Timestamp",
            "Call ID",
            "Action",
            "Details",
        ],
        datatype=[
            "str",
            "str",
            "str",
            "str",
        ],
        value=[],
        interactive=False,
        label="Recent Audit Events",
    )

    def refresh():
        metrics_md, langsmith_md, audit_rows = (
            get_observability_dashboard()
        )

        return (
            metrics_md,
            langsmith_md,
            audit_rows,
        )

    # Initial dashboard load.
    # gr.on(
    #     triggers=[gr.Load()],
    #     fn=refresh,
    #     inputs=[],
    #     outputs=[
    #         metrics,
    #         langsmith,
    #         audit_events,
    #     ],
    # )

    tab.select(
        fn=refresh,
        inputs=None,
        outputs=[
            metrics,
            langsmith,
            audit_events,
        ],
    )

    # tab.select(
    #     fn=refresh,
    #     inputs=[],
    #     outputs=[
    #         metrics,
    #         langsmith,
    #         audit_events,
    #     ],
    # )

    # Refresh whenever the user selects the tab.
    return metrics, langsmith, audit_events