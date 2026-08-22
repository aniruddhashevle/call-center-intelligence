import pytest
from pydantic import ValidationError

from src.graph.state import (
    QADimensionScore,
    QAScoreResult,
    TranscriptionSegment,
)


def test_transcription_confidence_rejects_value_above_one():
    with pytest.raises(ValidationError):
        TranscriptionSegment(
            start=0.0,
            end=1.0,
            text="hello",
            confidence=1.1,
        )


def test_transcription_confidence_rejects_value_below_zero():
    with pytest.raises(ValidationError):
        TranscriptionSegment(
            start=0.0,
            end=1.0,
            text="hello",
            confidence=-0.1,
        )


def test_qa_dimension_score_rejects_value_above_five():
    with pytest.raises(ValidationError):
        QADimensionScore(
            dimension="empathy",
            score=6,
        )


def test_qa_dimension_score_rejects_value_below_one():
    with pytest.raises(ValidationError):
        QADimensionScore(
            dimension="empathy",
            score=0,
        )


def test_overall_qa_score_rejects_value_above_five():
    with pytest.raises(ValidationError):
        QAScoreResult(overall_score=5.1)


def test_overall_qa_score_rejects_value_below_one():
    with pytest.raises(ValidationError):
        QAScoreResult(overall_score=0.9)