import re


PII_PATTERNS = [
    # Markdown email link:
    # [john@example.com](mailto:john@example.com)
    (
        re.compile(
            r"\[[A-Za-z0-9._%+-]+"
            r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\]"
            r"\(mailto:[^)]+\)",
            re.IGNORECASE,
        ),
        "EMAIL",
    ),
    (
        re.compile(
            r"\b\d{3}[- ]\d{2}[- ]\d{4}\b"
        ),
        "SSN",
    ),
    (
        re.compile(
            r"\b(?:\d{4}[- ]?){3}\d{4}\b"
        ),
        "CREDIT_CARD",
    ),
    (
        re.compile(
            r"\b[A-Za-z0-9._%+-]+"
            r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
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


def _find_pii_matches(text: str) -> list[dict]:
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

    # Earlier positions first.
    # For the same position, prefer the longer match.
    matches.sort(
        key=lambda item: (
            item["start"],
            -(item["end"] - item["start"]),
        )
    )

    deduplicated = []

    for match in matches:
        overlaps = False

        for existing in deduplicated:
            if (
                match["start"] < existing["end"]
                and match["end"] > existing["start"]
            ):
                overlaps = True
                break

        if not overlaps:
            deduplicated.append(match)

    return deduplicated


def redact_pii(text: str) -> str:
    """
    Replace detected PII with category placeholders.

    Examples:
        123-45-6789 -> [SSN]
        123 45 6789 -> [SSN]
        john@example.com -> [EMAIL]
        [john@example.com](mailto:john@example.com) -> [EMAIL]
    """

    matches = _find_pii_matches(text)

    # Replace right-to-left so original indexes remain valid.
    for match in reversed(matches):
        replacement = f"[{match['type']}]"

        text = (
            text[:match["start"]]
            + replacement
            + text[match["end"]:]
        )

    return text


def detect_pii(text: str) -> list[str]:
    """
    Return unique PII types detected in the text.

    The order follows the first occurrence
    of each PII type.
    """

    matches = _find_pii_matches(text)

    detected = []
    seen = set()

    for match in matches:
        pii_type = match["type"]

        if pii_type not in seen:
            detected.append(pii_type)
            seen.add(pii_type)

    return detected
