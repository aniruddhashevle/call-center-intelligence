from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet

from src.database.connection import get_session
from src.database.models import CallRecord
from src.graph.state import (
    CallReport,
    SummaryResult,
    QAScoreResult,
    TranscriptionResult,
)


def compile_report(
    call_id: str,
    summary: SummaryResult,
    qa_scores: QAScoreResult,
    transcription: TranscriptionResult | None = None,
) -> CallReport:
    """
    Assemble the final CallReport from upstream pipeline results.
    """

    return CallReport(
        call_id=call_id,
        summary=summary,
        qa_scores=qa_scores,
        transcription=transcription,
    )


def persist_report(
    report: CallReport,
    audio_filename: str | None = None,
    trace_id: str | None = None,
) -> None:
    """
    Persist a completed report into the CallRecord table.
    """

    session = get_session()

    try:
        record = (
            session.query(CallRecord)
            .filter_by(call_id=report.call_id)
            .first()
        )

        if record is None:
            record = CallRecord(
                call_id=report.call_id,
            )
            session.add(record)

        record.status = "completed"

        if audio_filename is not None:
            record.audio_filename = audio_filename

        record.transcript_text = (
            report.transcription.text
            if report.transcription is not None
            else None
        )

        record.summary_json = (
            report.summary.model_dump_json()
        )

        record.qa_scores_json = (
            report.qa_scores.model_dump_json()
        )

        record.report_json = (
            report.model_dump_json()
        )

        if trace_id is not None:
            record.trace_id = trace_id

        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def generate_report_json(report: CallReport) -> str:
    """
    Generate the JSON representation of a report.
    """

    return report.model_dump_json(indent=2)


def generate_report_pdf(report: CallReport) -> bytes:
    """
    Generate a PDF report and return it as bytes.
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "Call Center Intelligence Report",
            styles["Title"],
        )
    )

    story.append(
        Paragraph(
            f"Call ID: {report.call_id}",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 12))

    # Summary
    story.append(
        Paragraph(
            "Summary",
            styles["Heading2"],
        )
    )

    story.append(
        Paragraph(
            f"<b>Purpose:</b> "
            f"{report.summary.summary}",
            styles["Normal"],
        )
    )

    story.append(
        Paragraph(
            f"<b>Resolution:</b> "
            f"{report.summary.resolution_status.value}",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 12))

    # QA scores
    story.append(
        Paragraph(
            "QA Scores",
            styles["Heading2"],
        )
    )

    story.append(
        Paragraph(
            f"<b>Overall Score:</b> "
            f"{report.qa_scores.overall_score:.2f}/5",
            styles["Normal"],
        )
    )

    for dimension in report.qa_scores.dimension_scores:
        story.append(
            Paragraph(
                f"<b>{dimension.dimension}:</b> "
                f"{dimension.score}/5 — "
                f"{dimension.justification or ''}",
                styles["Normal"],
            )
        )

    story.append(Spacer(1, 12))

    # Compliance flags
    story.append(
        Paragraph(
            "Compliance Flags",
            styles["Heading2"],
        )
    )

    flags = report.qa_scores.compliance_flags

    if not flags:
        story.append(
            Paragraph(
                "No compliance flags.",
                styles["Normal"],
            )
        )
    else:
        for flag in flags:
            story.append(
                Paragraph(
                    f"<b>{flag.name}</b>: "
                    f"{flag.details or ''}",
                    styles["Normal"],
                )
            )

    document.build(story)

    return buffer.getvalue()