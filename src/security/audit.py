import json

from src.database.models import AuditLogEntry
from src.database.session import session_scope


class AuditLogger:
    @staticmethod
    def log(
        call_id: str,
        action: str,
        user: str,
        details: dict | None = None,
    ) -> None:
        entry = AuditLogEntry(
            call_id=call_id,
            action=action,
            user=user,
            details=json.dumps(details) if details is not None else None,
        )

        with session_scope() as session:
            session.add(entry)