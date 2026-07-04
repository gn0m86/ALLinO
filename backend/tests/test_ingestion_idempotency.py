from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.messages_repo import add_if_new, count_messages
from app.db.session import init_db
from app.domain.events import InboxMessage
from app.main import app
from app.services.dedup import dedup_key


# ---------------------------------------------------------------------------
# Pure unit tests — dedup_key and add_if_new without HTTP
# ---------------------------------------------------------------------------


def _msg(event_id: str, tenant_id: str, external_id: str, source: str = "mock") -> InboxMessage:
    return InboxMessage(
        event_id=event_id,
        tenant_id=tenant_id,
        source=source,
        external_id=external_id,
        timestamp=datetime.now(timezone.utc),
        preview="test",
        priority="normal",
    )


def test_dedup_key_is_deterministic() -> None:
    k1 = dedup_key("t1", "github", "ext-42")
    k2 = dedup_key("t1", "github", "ext-42")
    assert k1 == k2


def test_dedup_key_differs_by_tenant() -> None:
    k1 = dedup_key("tenant_a", "github", "ext-1")
    k2 = dedup_key("tenant_b", "github", "ext-1")
    assert k1 != k2


def test_dedup_key_differs_by_source() -> None:
    k1 = dedup_key("t1", "github", "ext-1")
    k2 = dedup_key("t1", "gitlab", "ext-1")
    assert k1 != k2


def test_add_if_new_inserts_once(tmp_path) -> None:
    session.DB_PATH = tmp_path / "dedup_once.db"
    init_db()

    msg = _msg("evt-1", "tenant_a", "ext-1")
    key = dedup_key("tenant_a", "mock", "ext-1")

    assert add_if_new(key, msg) is True
    assert add_if_new(key, msg) is False
    assert count_messages("tenant_a") == 1


def test_same_external_id_different_tenants_both_inserted(tmp_path) -> None:
    session.DB_PATH = tmp_path / "dedup_tenants.db"
    init_db()

    key_a = dedup_key("tenant_a", "mock", "shared-ext")
    key_b = dedup_key("tenant_b", "mock", "shared-ext")
    msg_a = _msg("evt-a", "tenant_a", "shared-ext")
    msg_b = _msg("evt-b", "tenant_b", "shared-ext")

    assert add_if_new(key_a, msg_a) is True
    assert add_if_new(key_b, msg_b) is True
    assert count_messages("tenant_a") == 1
    assert count_messages("tenant_b") == 1


# ---------------------------------------------------------------------------
# API-level idempotency via /events endpoint
# ---------------------------------------------------------------------------


def _event_payload(external_id: str, tenant_id: str = "tenant_demo") -> dict:
    return {
        "eventId": f"evt-{external_id}",
        "tenantId": tenant_id,
        "sourceType": "mock",
        "externalId": external_id,
        "timestamp": "2026-06-30T10:00:00Z",
        "payload": {"text": f"Event {external_id}"},
        "schemaVersion": "1.0.0",
    }


def test_events_endpoint_inserts_then_deduplicates(tmp_path) -> None:
    session.DB_PATH = tmp_path / "api_dedup.db"

    with TestClient(app) as client:
        r1 = client.post(
            "/api/v1/ingestion/events?tenant_id=tenant_demo",
            json=_event_payload("api-ext-1"),
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "inserted"

        r2 = client.post(
            "/api/v1/ingestion/events?tenant_id=tenant_demo",
            json=_event_payload("api-ext-1"),
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "duplicate"


def test_events_endpoint_rejects_tenant_mismatch(tmp_path) -> None:
    session.DB_PATH = tmp_path / "api_mismatch.db"

    payload = _event_payload("ext-mismatch", tenant_id="other_tenant")
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/ingestion/events?tenant_id=tenant_demo",
            json=payload,
        )
    assert r.status_code == 403


def test_connector_sync_deduplicates_duplicate_events(tmp_path) -> None:
    session.DB_PATH = tmp_path / "connector_dedup.db"

    notification = {
        "id": "gh-dedup-1",
        "updated_at": "2026-06-30T10:00:00Z",
        "reason": "mention",
        "subject": {"title": "Dedup test issue", "type": "Issue"},
        "repository": {"full_name": "org/repo"},
    }

    with TestClient(app) as client:
        r1 = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={"seeded_notifications": [notification]},
        )
        assert r1.status_code == 200
        assert r1.json()["inserted"] == 1
        assert r1.json()["duplicates"] == 0

        r2 = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={"seeded_notifications": [notification]},
        )
        assert r2.status_code == 200
        assert r2.json()["inserted"] == 0
        assert r2.json()["duplicates"] == 1
