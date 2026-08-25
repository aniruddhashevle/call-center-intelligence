from datetime import datetime
from uuid import uuid4

from src.database.connection import get_session, init_db
from src.database.models import AuditLogEntry, CallRecord


def test_call_record_insert_and_retrieve(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"

    monkeypatch.setenv(
        "DB_PATH",
        str(db_path),
    )

    init_db()

    session = get_session()
    call_id = f"call-test-{uuid4()}"

    try:
        record = CallRecord(
            call_id=call_id,
            status="completed",
            audio_filename="test.wav",
            transcript_text="Hello, I need help.",
            summary_json='{"summary": "Customer needs help."}',
            qa_scores_json='{"overall_score": 4.5}',
            report_json=f'{{"call_id": "{call_id}"}}',
            processed_at=datetime.utcnow(),
            trace_id="trace-test-001",
        )

        session.add(record)
        session.commit()

        retrieved = (
            session.query(CallRecord)
            .filter_by(call_id=call_id)
            .first()
        )

        assert retrieved is not None
        assert retrieved.call_id == call_id
        assert retrieved.report_json == f'{{"call_id": "{call_id}"}}'
        assert retrieved.status == "completed"
        assert retrieved.audio_filename == "test.wav"
        assert retrieved.transcript_text == (
            "Hello, I need help."
        )

    finally:
        session.close()


def test_audit_log_insert_and_retrieve(tmp_path, monkeypatch):
    db_path = tmp_path / "audit.db"

    monkeypatch.setenv(
        "DB_PATH",
        str(db_path),
    )

    init_db()

    session = get_session()

    try:
        entry = AuditLogEntry(
            call_id="call-test-002",
            action="test_action",
            user="system",
            timestamp=datetime.utcnow(),
            details='{"source": "test"}',
        )

        session.add(entry)
        session.commit()

        retrieved = (
            session.query(AuditLogEntry)
            .filter_by(call_id="call-test-002")
            .first()
        )

        assert retrieved is not None
        assert retrieved.call_id == "call-test-002"
        assert retrieved.action == "test_action"
        assert retrieved.user == "system"
        assert retrieved.details == (
            '{"source": "test"}'
        )

    finally:
        session.close()