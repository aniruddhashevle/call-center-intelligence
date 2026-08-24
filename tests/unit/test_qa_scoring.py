from unittest.mock import MagicMock, patch

import pytest

from src.agents.qa_scoring import (
    QAScoringError,
    _calculate_overall_score,
    score_call,
)
from src.graph.state import (
    QADimensionScore,
    QAScoreResult,
    ResolutionStatus,
    SummaryResult,
    TranscriptionResult,
    TranscriptionSegment,
)


def make_transcript():
    return TranscriptionResult(
        call_id="call-123",
        text="Hello, I need help.",
        segments=[
            TranscriptionSegment(
                start=0.0,
                end=3.0,
                text="Hello, how can I help?",
                confidence=0.95,
                speaker="Agent",
            ),
            TranscriptionSegment(
                start=3.5,
                end=6.0,
                text="I need help with my account.",
                confidence=0.92,
                speaker="Customer",
            ),
        ],
        language="en",
        duration_seconds=6.0,
    )


def make_summary():
    return SummaryResult(
        call_id="call-123",
        summary="Customer needs account assistance.",
        key_points=["Account assistance requested."],
        resolution_status=ResolutionStatus.unresolved,
        sentiment="neutral",
        action_items=[],
        entities=[],
    )


def make_qa_result(overall_score=3.0, score=3):
    dimensions = [
        "professionalism",
        "empathy",
        "problem_resolution",
        "compliance",
        "communication_clarity",
    ]

    return QAScoreResult(
        overall_score=overall_score,
        dimension_scores=[
            QADimensionScore(
                dimension=dimension,
                score=score,
                justification="Evidence at 00:01.",
            )
            for dimension in dimensions
        ],
        compliance_flags=[],
    )


def test_calculate_overall_score():
    result = make_qa_result(
        overall_score=3.0,
        score=5,
    )

    assert _calculate_overall_score(result) == 5.0


@patch("src.agents.qa_scoring.get_llm")
@patch("src.agents.qa_scoring.build_config")
def test_score_call_recomputes_overall_score(
    mock_config,
    mock_get_llm,
):
    mock_config.return_value.max_retries_per_node = 3
    mock_config.return_value.llm_timeout_seconds = 60
    mock_config.return_value.llm_provider = "openai"

    structured_llm = MagicMock()

    # Deliberately wrong LLM overall score.
    structured_llm.invoke.return_value = make_qa_result(
        overall_score=3.0,
        score=5,
    )

    llm = MagicMock()
    llm.with_structured_output.return_value = structured_llm

    mock_get_llm.return_value = llm

    result = score_call(
        make_transcript(),
        make_summary(),
    )

    assert result.overall_score == 5.0
    assert structured_llm.invoke.call_count == 1


@patch("src.agents.qa_scoring.time.sleep")
@patch("src.agents.qa_scoring.get_llm")
@patch("src.agents.qa_scoring.build_config")
def test_qa_scoring_retries_then_succeeds(
    mock_config,
    mock_get_llm,
    mock_sleep,
):
    mock_config.return_value.max_retries_per_node = 3
    mock_config.return_value.llm_timeout_seconds = 60
    mock_config.return_value.llm_provider = "openai"

    structured_llm = MagicMock()

    structured_llm.invoke.side_effect = [
        Exception("temporary API failure"),
        make_qa_result(overall_score=3.0, score=4),
    ]

    llm = MagicMock()
    llm.with_structured_output.return_value = structured_llm

    mock_get_llm.return_value = llm

    result = score_call(
        make_transcript(),
        make_summary(),
    )

    assert result.overall_score == 4.0
    assert structured_llm.invoke.call_count == 2

    mock_sleep.assert_called_once_with(1)


@patch("src.agents.qa_scoring.time.sleep")
@patch("src.agents.qa_scoring.get_llm")
@patch("src.agents.qa_scoring.build_config")
def test_qa_scoring_error_after_max_retries(
    mock_config,
    mock_get_llm,
    mock_sleep,
):
    mock_config.return_value.max_retries_per_node = 3
    mock_config.return_value.llm_timeout_seconds = 60
    mock_config.return_value.llm_provider = "openai"

    structured_llm = MagicMock()
    structured_llm.invoke.side_effect = Exception(
        "API unavailable"
    )

    llm = MagicMock()
    llm.with_structured_output.return_value = structured_llm

    mock_get_llm.return_value = llm

    with pytest.raises(QAScoringError):
        score_call(
            make_transcript(),
            make_summary(),
        )

    assert structured_llm.invoke.call_count == 3
    assert mock_sleep.call_count == 2