from datetime import datetime, timezone

from app.connectors.discord_connector import map_discord_message_to_unified_event
from app.connectors.rocketchat_connector import map_rocketchat_message_to_unified_event
from app.connectors.slack_connector import map_slack_message_to_unified_event
from app.domain.events import UnifiedEvent
from app.services.normalizer import normalize_event


def _event(external_id: str, payload: dict) -> UnifiedEvent:
    return UnifiedEvent(
        eventId=f"evt-{external_id}",
        tenantId="tenant_demo",
        sourceType="github",
        externalId=external_id,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
        schemaVersion="1.0.0",
    )


def test_thread_key_is_stable_for_same_subject_url() -> None:
    e1 = _event("n-1", {"subject_url": "https://api.github.com/repos/org/repo/issues/1", "text": "A"})
    e2 = _event("n-2", {"subject_url": "https://api.github.com/repos/org/repo/issues/1", "text": "B"})

    m1 = normalize_event(e1)
    m2 = normalize_event(e2)
    assert m1.thread_key == m2.thread_key


def test_thread_key_differs_for_different_subject_url() -> None:
    e1 = _event("n-1", {"subject_url": "https://api.github.com/repos/org/repo/issues/1"})
    e2 = _event("n-2", {"subject_url": "https://api.github.com/repos/org/repo/issues/2"})

    m1 = normalize_event(e1)
    m2 = normalize_event(e2)
    assert m1.thread_key != m2.thread_key


def test_thread_key_falls_back_to_external_id_when_no_anchor() -> None:
    e1 = _event("abc-123", {"text": "hello"})
    e2 = _event("abc-456", {"text": "world"})

    m1 = normalize_event(e1)
    m2 = normalize_event(e2)
    assert m1.thread_key
    assert m2.thread_key
    assert m1.thread_key != m2.thread_key


def test_thread_key_groups_non_url_events_by_semantic_payload_anchor() -> None:
    e1 = _event(
        "gl-100",
        {
            "project": "org/platform",
            "target_type": "MergeRequest",
            "text": "org/platform | Fix auth regression | commented",
        },
    )
    e2 = _event(
        "gl-101",
        {
            "project": "org/platform",
            "target_type": "MergeRequest",
            "text": "org/platform | Fix auth regression | approved",
        },
    )

    m1 = normalize_event(e1)
    m2 = normalize_event(e2)
    assert m1.thread_key == m2.thread_key


def test_thread_key_separates_non_url_events_with_different_semantic_anchor() -> None:
    e1 = _event(
        "gl-200",
        {
            "project": "org/platform",
            "target_type": "MergeRequest",
            "text": "org/platform | Fix auth regression",
        },
    )
    e2 = _event(
        "gl-201",
        {
            "project": "org/billing",
            "target_type": "MergeRequest",
            "text": "org/billing | Fix auth regression",
        },
    )

    m1 = normalize_event(e1)
    m2 = normalize_event(e2)
    assert m1.thread_key != m2.thread_key


def _as_event(raw: dict) -> UnifiedEvent:
    return UnifiedEvent(
        eventId=raw["eventId"],
        tenantId=raw["tenantId"],
        sourceType=raw["sourceType"],
        externalId=raw["externalId"],
        timestamp=datetime.fromisoformat(raw["timestamp"]),
        payload=raw["payload"],
        schemaVersion=raw["schemaVersion"],
    )


def test_thread_key_groups_rocketchat_messages_by_channel_not_message() -> None:
    """Regression test for a real bug found live (Sprint 31): `identifier` used to be
    set to the message-unique external_id, so every single chat message became its
    own isolated "thread" instead of grouping by channel."""
    raw1 = map_rocketchat_message_to_unified_event(
        {"_id": "m1", "ts": "2026-07-03T12:00:00Z", "msg": "first", "rid": "GENERAL", "u": {"username": "a"}},
        tenant_id="tenant_demo",
    )
    raw2 = map_rocketchat_message_to_unified_event(
        {"_id": "m2", "ts": "2026-07-03T12:05:00Z", "msg": "second", "rid": "GENERAL", "u": {"username": "b"}},
        tenant_id="tenant_demo",
    )

    m1 = normalize_event(_as_event(raw1))
    m2 = normalize_event(_as_event(raw2))
    assert m1.thread_key == m2.thread_key


def test_thread_key_separates_rocketchat_messages_from_different_channels() -> None:
    raw1 = map_rocketchat_message_to_unified_event(
        {"_id": "m1", "ts": "2026-07-03T12:00:00Z", "msg": "hi", "rid": "GENERAL", "u": {}},
        tenant_id="tenant_demo",
    )
    raw2 = map_rocketchat_message_to_unified_event(
        {"_id": "m2", "ts": "2026-07-03T12:00:00Z", "msg": "hi", "rid": "other-room", "u": {}},
        tenant_id="tenant_demo",
    )

    m1 = normalize_event(_as_event(raw1))
    m2 = normalize_event(_as_event(raw2))
    assert m1.thread_key != m2.thread_key


def test_thread_key_groups_slack_messages_by_channel_not_message() -> None:
    raw1 = map_slack_message_to_unified_event(
        {"ts": "1000.0001", "text": "first", "channel": "C1", "user": "u1"}, tenant_id="tenant_demo"
    )
    raw2 = map_slack_message_to_unified_event(
        {"ts": "1001.0002", "text": "second", "channel": "C1", "user": "u2"}, tenant_id="tenant_demo"
    )

    m1 = normalize_event(_as_event(raw1))
    m2 = normalize_event(_as_event(raw2))
    assert m1.thread_key == m2.thread_key


def test_thread_key_groups_discord_messages_by_channel_not_message() -> None:
    raw1 = map_discord_message_to_unified_event(
        {"id": "1", "timestamp": "2026-07-03T12:00:00Z", "content": "first", "channel_id": "chan1", "author": {}},
        tenant_id="tenant_demo",
    )
    raw2 = map_discord_message_to_unified_event(
        {"id": "2", "timestamp": "2026-07-03T12:05:00Z", "content": "second", "channel_id": "chan1", "author": {}},
        tenant_id="tenant_demo",
    )

    m1 = normalize_event(_as_event(raw1))
    m2 = normalize_event(_as_event(raw2))
    assert m1.thread_key == m2.thread_key
