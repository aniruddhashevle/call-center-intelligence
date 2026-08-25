import logging
import os

from src.agents.transcription import _get_whisper_model
from src.graph.workflow import compile_workflow
from src.security.audit import AuditLogger
from src.ui.app import build_app
from src.utils.config import build_config
from src.database.connection import get_engine, init_db


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    config = build_config()

    engine = get_engine()
    init_db()

    logger.info(
        "Whisper model size: %s",
        config.whisper_model_size,
    )

    _get_whisper_model(config.whisper_model_size)

    workflow = compile_workflow(
        config,
        db_engine=engine,
    )

    audit_logger = AuditLogger()

    app = build_app(
        # workflow=workflow,
        # audit_logger=audit_logger,
    )

    is_spaces = bool(os.getenv("SPACE_ID"))

    app.launch(
        server_name="0.0.0.0" if is_spaces else "127.0.0.1",
        server_port=7860,
    )


if __name__ == "__main__":
    main()