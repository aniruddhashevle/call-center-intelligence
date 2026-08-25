from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CallRecord(Base):
    __tablename__ = "call_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    call_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    audio_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    transcript_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    summary_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    qa_scores_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    report_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    trace_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    call_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    user: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class TranscriptionCache(Base):
    __tablename__ = "transcription_cache"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    audio_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    transcription_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )