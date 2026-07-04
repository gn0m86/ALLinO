from ..domain.events import UnifiedEvent

_HIGH_KEYWORDS = frozenset(
    [
        "error", "fail", "failed", "failure", "critical", "urgent",
        "alert", "security", "breach", "vulnerability", "cve",
        "incident", "down", "outage", "crash", "exploit", "panic",
        "emergency", "sev1", "p0", "p1",
    ]
)
_MEDIUM_KEYWORDS = frozenset(
    [
        "warning", "warn", "review", "attention", "fix", "bug",
        "todo", "task", "issue", "deprecat", "slow", "timeout",
        "sev2", "p2",
    ]
)
_HIGH_SOURCES = frozenset(["incident", "pagerduty", "opsgenie", "alertmanager"])


def classify_priority(event: UnifiedEvent) -> str:
    """Return 'high', 'medium', or 'normal' based on event content."""
    source_lower = event.sourceType.lower()
    if any(s in source_lower for s in _HIGH_SOURCES):
        return "high"

    texts: list[str] = [source_lower, event.externalId.lower()]
    if isinstance(event.payload, dict):
        for v in event.payload.values():
            if isinstance(v, str):
                texts.append(v.lower())

    combined = " ".join(texts)

    if any(kw in combined for kw in _HIGH_KEYWORDS):
        return "high"
    if any(kw in combined for kw in _MEDIUM_KEYWORDS):
        return "medium"
    return "normal"
