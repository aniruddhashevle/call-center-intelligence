from unittest.mock import MagicMock, patch

import pytest

from src.agents.summarization import (
    SummarizationError,
    _format_transcript,
    summarize_transcript,
)
from src.graph.state import (
    ResolutionStatus,
    SummaryResult,
    TranscriptionResult,
    TranscriptionSegment,
)


def make_transcript():
    return TranscriptionResult(
        call_id="call-123",
        text="Hello, I need help with my account.",
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
                end=7.0,
                text="I need help with my account.",
                confidence=0.92,
                speaker="Customer",
            ),
        ],
        language="en",
        duration_seconds=7.0,
    )


def make_summary():
    return SummaryResult(
        call_id="temporary",
        summary="Customer requested account assistance.",
        key_points=["Customer needs account assistance."],
        resolution_status=ResolutionStatus.unresolved,
        sentiment="neutral",
        action_items=[],
        entities=[],
    )


def test_format_transcript():
    transcript = make_transcript()

    result = _format_transcript(transcript)

    assert "[00:00-00:03] Agent: Hello, how can I help?" in result
    assert (
        "[00:03-00:07] Customer: "
        "I need help with my account."
    ) in result


@patch("src.agents.summarization.get_llm")
@patch("src.agents.summarization.build_config")
def test_summarize_transcript(mock_config, mock_get_llm):
    mock_config.return_value.max_retries_per_node = 3
    mock_config.return_value.llm_timeout_seconds = 60
    mock_config.return_value.llm_provider = "openai"

    structured_llm = MagicMock()
    structured_llm.invoke.return_value = make_summary()

    llm = MagicMock()
    llm.with_structured_output.return_value = structured_llm

    mock_get_llm.return_value = llm

    transcript = make_transcript()

    result = summarize_transcript(transcript)

    assert result.call_id == "call-123"
    assert result.summary == (
        "Customer requested account assistance."
    )

    structured_llm.invoke.assert_called_once()


@patch("src.agents.summarization.time.sleep")
@patch("src.agents.summarization.get_llm")
@patch("src.agents.summarization.build_config")
def test_summarization_retries_then_succeeds(
    mock_config,
    mock_get_llm,
    mock_sleep,
):
    mock_config.return_value.max_retries_per_node = 3
    mock_config.return_value.llm_timeout_seconds = 60
    mock_config.return_value.llm_provider = "openai"

    structured_llm = MagicMock()

    structured_llm.invoke.side_effect = [
        Exception("temporary failure"),
        make_summary(),
    ]

    llm = MagicMock()
    llm.with_structured_output.return_value = structured_llm

    mock_get_llm.return_value = llm

    result = summarize_transcript(make_transcript())

    assert result.call_id == "call-123"
    assert structured_llm.invoke.call_count == 2

    mock_sleep.assert_called_once_with(1)


@patch("src.agents.summarization.time.sleep")
@patch("src.agents.summarization.get_llm")
@patch("src.agents.summarization.build_config")
def test_summarization_error_after_max_retries(
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

    with pytest.raises(SummarizationError):
        summarize_transcript(make_transcript())

    assert structured_llm.invoke.call_count == 3
    assert mock_sleep.call_count == 2