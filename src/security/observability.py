# src/services/observability.py

from __future__ import annotations

import json

from src.database.models import AuditLogEntry, CallRecord
from src.database.session import session_scope


def get_observability_dashboard() -> tuple[
    str,
    str,
    list[list[str]],
]:
    """
    Return dashboard metrics, LangSmith status, and recent audit events.

    All database reads happen inside a single session_scope().
    """

    with session_scope() as session:
        total_calls = session.query(CallRecord).count()

        completed_calls = (
            session.query(CallRecord)
            .filter(CallRecord.status == "completed")
            .count()
        )

        failed_calls = (
            session.query(CallRecord)
            .filter(CallRecord.status == "failed")
            .count()
        )

        flagged_calls = (
            session.query(CallRecord)
            .filter(
                CallRecord.status.in_(
                    [
                        "flagged_for_review",
                        "supervisor_review",
                    ]
                )
            )
            .count()
        )

        records = (
            session.query(CallRecord)
            .filter(CallRecord.qa_scores_json.isnot(None))
            .all()
        )

        qa_scores: list[float] = []

        for record in records:
            try:
                data = json.loads(record.qa_scores_json)

                score = data.get("overall_score")

                if score is not None:
                    qa_scores.append(float(score))

            except (TypeError, ValueError, json.JSONDecodeError):
                continue

        average_qa = (
            sum(qa_scores) / len(qa_scores)
            if qa_scores
            else 0.0
        )

        total_compliance_flags = 0

        for record in records:
            try:
                data = json.loads(record.qa_scores_json)

                flags = data.get("compliance_flags", [])

                total_compliance_flags += sum(
                    1
                    for flag in flags
                    if flag.get("triggered", False)
                )

            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                continue

        total_audit_events = session.query(
            AuditLogEntry
        ).count()

        recent_events = (
            session.query(AuditLogEntry)
            .order_by(
                AuditLogEntry.timestamp.desc()
            )
            .limit(20)
            .all()
        )

        audit_rows: list[list[str]] = []

        for event in recent_events:
            audit_rows.append(
                [
                    event.timestamp.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    event.call_id,
                    event.action,
                    event.details or "",
                ]
            )

    success_rate = (
        (completed_calls / total_calls) * 100
        if total_calls
        else 0.0
    )

    metrics_md = f"""
### Pipeline Metrics

| Metric | Value |
|---|---:|
| Total calls | {total_calls} |
| Completed | {completed_calls} |
| Failed | {failed_calls} |
| Flagged / supervisor review | {flagged_calls} |
| Success rate | {success_rate:.1f}% |
| Average QA score | {average_qa:.2f}/5 |
| Compliance flags | {total_compliance_flags} |
| Audit events | {total_audit_events} |
"""

    langsmith_enabled = bool(
        __import__("os").getenv("LANGCHAIN_API_KEY")
    )

    if langsmith_enabled:
        langsmith_md = (
            "### LangSmith\n\n"
            "🟢 **Configured** — "
            "LANGCHAIN_API_KEY is present."
        )
    else:
        langsmith_md = (
            "### LangSmith\n\n"
            "⚪ **Not configured** — "
            "LANGCHAIN_API_KEY is not set."
        )

    return (
        metrics_md.strip(),
        langsmith_md.strip(),
        audit_rows,
    )