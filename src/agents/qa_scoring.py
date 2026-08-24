# src/agents/qa_scoring.py

import time

from src.graph.state import (
    QAScoreResult,
    SummaryResult,
    TranscriptionResult,
)
from src.utils.config import build_config
from src.utils.formatters import secs_to_mmss
from src.utils.llm_factory import get_llm


DIMENSION_WEIGHTS = {
    "professionalism": 0.15,
    "empathy": 0.20,
    "problem_resolution": 0.30,
    "compliance": 0.20,
    "communication_clarity": 0.15,
}

class QAScoringError(Exception):
    """Raised when QA scoring fails after all retries."""


def _format_transcript(
    transcript: TranscriptionResult,
) -> str:
    lines = []

    for segment in transcript.segments:
        speaker = segment.speaker or "Unknown"

        lines.append(
            f"[{secs_to_mmss(segment.start)}-"
            f"{secs_to_mmss(segment.end)}] "
            f"{speaker}: {segment.text}"
        )

    return "\n".join(lines)

SYSTEM_PROMPT = """
You are a professional call-center quality assurance coach.

## Scoring philosophy

Use 3/5 as the baseline for competent handling.

Do not inflate scores simply because the interaction was pleasant.
Scores must be supported by observable behavior in the transcript.

## Dimensions

### Professionalism
1 = Unprofessional, rude, dismissive, or inappropriate.
2 = Significant professionalism problems.
3 = Competent and professional.
4 = Consistently professional with strong ownership.
5 = Exceptional professionalism and ownership.

### Empathy
1 = Ignores customer concerns or shows hostility.
2 = Limited acknowledgment of customer concerns.
3 = Adequately acknowledges customer needs.
4 = Clearly demonstrates empathy and understanding.
5 = Exceptional empathy with personalized emotional support.

### Problem Resolution
1 = Does not address the customer's problem.
2 = Provides little or ineffective assistance.
3 = Adequately addresses the issue.
4 = Resolves the issue effectively with good ownership.
5 = Exceptional resolution with proactive problem prevention.

### Compliance
1 = Serious procedural or policy violations.
2 = Significant compliance concerns.
3 = Meets required procedures.
4 = Strong adherence to procedures.
5 = Exceptional compliance and risk awareness.

### Communication Clarity
1 = Confusing, incomplete, or difficult to understand.
2 = Frequently unclear.
3 = Clear enough for competent handling.
4 = Consistently clear and well structured.
5 = Exceptionally clear, concise, and easy to understand.

## Justifications

For every dimension, explain the score using specific evidence
from the transcript.

When possible, cite timestamps in MM:SS format.

Write like a real coaching review, not like a generic AI evaluation.

## Compliance flags

Only flag genuine procedural or policy violations.
Do not flag stylistic preferences as compliance issues.

## Short calls

A short call can be efficient and successful.
Do not penalize a call simply because it is short.
"""


def _calculate_overall_score(result: QAScoreResult) -> float:
    """Calculate the weighted overall QA score."""

    weighted_total = 0.0
    total_weight = 0.0

    for dimension in result.dimension_scores:
        dimension_name = dimension.dimension.strip().lower()

        weight = DIMENSION_WEIGHTS.get(dimension_name)

        if weight is None:
            continue

        weighted_total += dimension.score * weight
        total_weight += weight

    if total_weight == 0:
        raise QAScoringError(
            "LLM returned no recognized QA dimensions."
        )

    return round(weighted_total / total_weight, 2)


def score_call(
    transcript: TranscriptionResult,
    summary: SummaryResult,
) -> QAScoreResult:
    """
    Score a call using the transcript and generated summary.

    The LLM provides dimension-level scores, but the overall
    score is always calculated deterministically by this code.
    """

    config = build_config()

    llm = get_llm(
        provider=config.llm_provider,
        timeout=config.llm_timeout_seconds,
    )

    structured_llm = llm.with_structured_output(
        QAScoreResult
    )

    transcript_text = _format_transcript(transcript)

    summary_text = (
        f"Summary: {summary.summary}\n"
        f"Resolution status: "
        f"{summary.resolution_status.value}\n"
        f"Sentiment: {summary.sentiment}\n"
    )

    messages = [
        ("system", SYSTEM_PROMPT),
        (
            "user",
            f"Call ID: {transcript.call_id}\n\n"
            f"{summary_text}\n\n"
            f"Transcript:\n{transcript_text}",
        ),
    ]

    max_retries = config.max_retries_per_node

    for attempt in range(max_retries):
        try:
            result = structured_llm.invoke(messages)

            result.overall_score = _calculate_overall_score(
                result
            )

            return result

        except Exception as exc:
            if attempt == max_retries - 1:
                raise QAScoringError(
                    "QA scoring failed after "
                    f"{max_retries} attempts"
                ) from exc

            time.sleep(min(2 ** attempt, 10))

    raise QAScoringError("QA scoring failed")