from __future__ import annotations

import gradio as gr

from src.ui.tabs.analyze import build_analyze_tab
from src.ui.tabs.observability import build_observability_tab


def build_app():
    with gr.Blocks(
        title="Call Center Intelligence",
    ) as app:
        with gr.Tabs():
            with gr.Tab("Analyze Call"):
                build_analyze_tab()

            with gr.Tab("Observability") as observability_tab:
                build_observability_tab(observability_tab)

    return app