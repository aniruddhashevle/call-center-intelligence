from datetime import datetime
from enum import StrEnum
from typing import TypedDict

from pydantic import BaseModel, Field


class AudioInput(BaseModel):
    audio_data: bytes
    filename: str
    caller_id: str | None = None
    department: str | None = None
    timestamp: datetime | None = None
    original_file_path: str | None = None


class AudioProperties(BaseModel):
    format: str
    frame_count: int
    sample_rate: int
    channel_count: int
    duration_seconds: float


class PIIScanResult(BaseModel):
    pii_detected: bool = False
    affected_fields: list[str] = Field(default_factory=list)


class IntakeResult(BaseModel):
    call_id: str
    validation_passed: bool
    audio_properties: AudioProperties
    pii_scan: PIIScanResult
    original_file_path: str | None = None
    temp_file_path: str | None = None
    error: str | None = None


class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    speaker: str | None = None


class TranscriptionResult(BaseModel):
    call_id: str
    text: str
    segments: list[TranscriptionSegment] = Field(default_factory=list)
    language: str | None = None
    duration_seconds: float | None = None


class ResolutionStatus(StrEnum):
    resolved = "resolved"
    unresolved = "unresolved"
    escalated = "escalated"


class ActionItem(BaseModel):
    description: str
    owner: str | None = None
    due_date: datetime | None = None


class Entity(BaseModel):
    name: str
    entity_type: str


class SummaryResult(BaseModel):
    call_id: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    resolution_status: ResolutionStatus
    sentiment: str
    action_items: list[ActionItem] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)


class QADimensionScore(BaseModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    justification: str | None = None
    feedback: str | None = None


class ComplianceFlag(BaseModel):
    name: str
    triggered: bool
    details: str | None = None
    severity: str = "info"


class QAScoreResult(BaseModel):
    overall_score: float = Field(ge=1.0, le=5.0)
    dimension_scores: list[QADimensionScore] = Field(default_factory=list)
    compliance_flags: list[ComplianceFlag] = Field(default_factory=list)


class CallReport(BaseModel):
    call_id: str
    summary: SummaryResult
    qa_scores: QAScoreResult
    transcription: TranscriptionResult | None = None


class PipelineState(TypedDict, total=False):
    audio_input: AudioInput
    intake: IntakeResult
    transcription: TranscriptionResult
    transcript_pii_scan: PIIScanResult
    summary: SummaryResult
    qa_scores: QAScoreResult
    report: CallReport
    error: str
    status: str