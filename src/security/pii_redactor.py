import re


PII_PATTERNS = [
    (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "SSN",
    ),
    (
        re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
        "CREDIT_CARD",
    ),
    (
        re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
        "EMAIL",
    ),
    (
        re.compile(
            r"(?<!\d)"
            r"(?:\+?1[-.\s]?)?"
            r"(?:\(?\d{3}\)?[-.\s]?)"
            r"\d{3}[-.\s]\d{4}"
            r"(?!\d)"
        ),
        "PHONE",
    ),
]


def _find_pii_matches(text: str):
    """Find and deduplicate PII matches."""

    matches = []

    for pattern, pii_type in PII_PATTERNS:
        for match in pattern.finditer(text):
            matches.append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "type": pii_type,
                    "value": match.group(),
                }
            )

    # Earlier start position first.
    # For equal starts, prefer the longer match.
    matches.sort(
        key=lambda item: (
            item["start"],
            -(item["end"] - item["start"]),
        )
    )

    deduplicated = []

    for match in matches:
        if not deduplicated:
            deduplicated.append(match)
            continue

        previous = deduplicated[-1]

        # Overlapping match.
        if match["start"] < previous["end"]:
            continue

        deduplicated.append(match)

    return deduplicated


def redact_pii(text: str) -> str:
    """
    Replace detected PII with category placeholders.

    Example:
        123-45-6789
        ->
        [SSN]
    """

    matches = _find_pii_matches(text)

    # Replace right-to-left so earlier positions remain valid.
    for match in reversed(matches):
        replacement = f"[{match['type']}]"

        text = (
            text[:match["start"]]
            + replacement
            + text[match["end"]:]
        )

    return text


def detect_pii(text: str) -> list[str]:
    """Return the PII types detected in text."""

    matches = _find_pii_matches(text)

    return [match["type"] for match in matches]