def secs_to_mmss(seconds: float) -> str:
    """Convert seconds to MM:SS."""
    total_seconds = max(0, int(seconds))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def format_summary(d) -> str:
    """Format a SummaryResult as readable Markdown."""

    lines = [
        "## Call Purpose",
        d.summary,
        "",
        "## Key Discussion Points",
    ]

    for item in d.key_points:
        lines.append(f"- {item}")

    lines.extend([
        "",
        "## Action Items",
    ])

    if d.action_items:
        for item in d.action_items:
            owner = f" — Owner: {item.owner}" if item.owner else ""
            lines.append(f"- {item.description}{owner}")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Resolution Status",
        d.resolution_status.value,
        "",
        "## Sentiment",
        d.sentiment,
        "",
        "## Entities",
    ])

    if d.entities:
        for entity in d.entities:
            lines.append(f"- {entity.name} ({entity.entity_type})")
    else:
        lines.append("- None")

    return "\n".join(lines)


def format_qa(d) -> str:
    """Format a QAScoreResult as readable Markdown."""

    lines = [
        "## Overall Score",
        f"{d.overall_score:.2f}/5.0",
        "",
        "## Dimension Scores",
    ]

    for dimension in d.dimension_scores:
        lines.append(
            f"- **{dimension.dimension}**: "
            f"{dimension.score}/5"
        )

        if dimension.feedback:
            lines.append(f"  - {dimension.feedback}")

    lines.extend([
        "",
        "## Compliance Flags",
    ])

    if not d.compliance_flags:
        lines.append("- ℹ️ None")
    else:
        severity_icons = {
            "info": "ℹ️",
            "low": "⚠️",
            "medium": "🔶",
            "high": "🔴",
        }

        for flag in d.compliance_flags:
            icon = severity_icons.get(
                flag.severity.lower(),
                "⚠️",
            )
            lines.append(
                f"- {icon} **{flag.name}**: "
                f"{flag.details or ''}"
            )

    return "\n".join(lines)