from datetime import datetime, timezone

from app.domain.events import UnifiedEvent
from app.services.priority_classifier import classify_priority


def _event(source: str, external_id: str, payload: dict) -> UnifiedEvent:
    return UnifiedEvent(
        eventId="evt-1",
        tenantId="tenant_demo",
        sourceType=source,
        externalId=external_id,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
        schemaVersion="1.0.0",
    )


def test_incident_source_is_high() -> None:
    assert classify_priority(_event("incident", "inc-1", {"text": "server down"})) == "high"


def test_error_keyword_in_payload_is_high() -> None:
    assert classify_priority(_event("github", "pr-1", {"text": "build failed"})) == "high"


def test_security_keyword_is_high() -> None:
    assert classify_priority(_event("github", "issue-1", {"text": "security vulnerability found"})) == "high"


def test_outage_keyword_is_high() -> None:
    assert classify_priority(_event("linear", "task-1", {"text": "database outage detected"})) == "high"


def test_review_keyword_is_medium() -> None:
    assert classify_priority(_event("github", "pr-2", {"text": "please review this PR"})) == "medium"


def test_bug_keyword_is_medium() -> None:
    assert classify_priority(_event("linear", "task-2", {"text": "fix the bug in login"})) == "medium"


def test_normal_event() -> None:
    assert classify_priority(_event("github", "pr-3", {"text": "add new feature"})) == "normal"


def test_empty_payload_is_normal() -> None:
    assert classify_priority(_event("github", "pr-4", {})) == "normal"


def test_high_beats_medium_when_both_present() -> None:
    assert classify_priority(_event("github", "pr-5", {"text": "critical bug fix required"})) == "high"
