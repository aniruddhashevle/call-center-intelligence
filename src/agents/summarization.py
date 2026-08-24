import time

from src.graph.state import SummaryResult, TranscriptionResult
from src.utils.config import build_config
from src.utils.llm_factory import get_llm
from src.utils.formatters import secs_to_mmss


class SummarizationError(Exception):
    """Raised when summarization fails after all retries."""


def _format_transcript(transcript: TranscriptionResult) -> str:
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
You are a professional call-center quality analyst.

Analyze the provided call transcript and produce a structured summary.

Identify:
- the purpose of the call
- the key discussion points
- the resolution status
- the overall customer sentiment
- action items
- important entities

Be factual. Do not invent information that is not present
in the transcript.
"""


def summarize_transcript(
    transcript: TranscriptionResult,
) -> SummaryResult:

    config = build_config()

    llm = get_llm(
        provider=config.llm_provider,
        timeout=config.llm_timeout_seconds,
    )

    structured_llm = llm.with_structured_output(
        SummaryResult
    )

    transcript_text = _format_transcript(transcript)

    messages = [
        ("system", SYSTEM_PROMPT),
        (
            "user",
            f"Call ID: {transcript.call_id}\n\n"
            f"Transcript:\n{transcript_text}",
        ),
    ]

    max_retries = config.max_retries_per_node

    for attempt in range(max_retries):
        try:
            result = structured_llm.invoke(messages)

            result.call_id = transcript.call_id

            return result

        except Exception as exc:
            if attempt == max_retries - 1:
                raise SummarizationError(
                    "Summarization failed after "
                    f"{max_retries} attempts"
                ) from exc

            time.sleep(min(2 ** attempt, 10))

    raise SummarizationError("Summarization failed")