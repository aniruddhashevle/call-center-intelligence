import json

from src.database.models import AuditLogEntry
from src.database.session import SessionLocal, init_db
from src.security.audit import AuditLogger


def test_audit_logger_writes_entry():
    init_db()

    AuditLogger.log(
        call_id="test-call-123",
        action="pii_detected",
        user="system",
        details={
            "field": "caller_id",
            "type": "SSN",
        },
    )

    with SessionLocal() as session:
        entry = (
            session.query(AuditLogEntry)
            .filter_by(call_id="test-call-123")
            .first()
        )

    assert entry is not None
    assert entry.action == "pii_detected"
    assert entry.user == "system"

    details = json.loads(entry.details)

    assert details["field"] == "caller_id"
    assert details["type"] == "SSN"