from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import session
from app.db.session import get_connection
from app.main import app


def _seed_event(
    client: TestClient,
    event_id: str,
    text: str = "normal update",
    tenant_id: str = "tenant_demo",
    source_type: str = "github",
) -> None:
    resp = client.post(
        f"/api/v1/ingestion/events?tenant_id={tenant_id}",
        json={
            "eventId": event_id,
            "tenantId": tenant_id,
            "sourceType": source_type,
            "externalId": event_id,
            "timestamp": "2026-07-03T12:00:00Z",
            "payload": {"text": text},
            "schemaVersion": "1.0.0",
        },
    )
    assert resp.status_code == 200


def _backdate_created_at(event_id: str, tenant_id: str, hours_ago: float) -> None:
    backdated = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE messages SET created_at = ? WHERE tenant_id = ? AND event_id = ?",
            (backdated, tenant_id, event_id),
        )
        conn.commit()


def _digest(client: TestClient, tenant_id: str = "tenant_demo", hours: int | None = None) -> dict:
    url = f"/api/v1/ingestion/digest?tenant_id={tenant_id}"
    if hours is not None:
        url += f"&hours={hours}"
    resp = client.get(url)
    assert resp.status_code == 200
    return resp.json()


def test_digest_counts_recent_messages_by_source_and_priority(tmp_path) -> None:
    session.DB_PATH = tmp_path / "digest_counts.db"

    with TestClient(app) as client:
        _seed_event(client, "d1", "routine update", source_type="github")
        _seed_event(client, "d2", "critical outage in prod", source_type="github")
        _seed_event(client, "d3", "routine update", source_type="slack")

        digest = _digest(client)
        assert digest["total"] == 3
        assert digest["by_source"] == {"github": 2, "slack": 1}
        assert digest["by_priority"]["high"] == 1
        assert digest["by_priority"]["normal"] == 2


def test_digest_highlights_only_high_priority_messages(tmp_path) -> None:
    session.DB_PATH = tmp_path / "digest_highlights.db"

    with TestClient(app) as client:
        _seed_event(client, "h1", "routine update")
        _seed_event(client, "h2", "critical security breach")

        digest = _digest(client)
        highlight_ids = [h["event_id"] for h in digest["highlights"]]
        assert highlight_ids == ["h2"]


def test_digest_excludes_messages_older_than_window(tmp_path) -> None:
    session.DB_PATH = tmp_path / "digest_window.db"

    with TestClient(app) as client:
        _seed_event(client, "recent-1")
        _seed_event(client, "old-1")
        _backdate_created_at("old-1", "tenant_demo", hours_ago=48)

        digest = _digest(client, hours=24)
        assert digest["total"] == 1
        assert digest["since_hours"] == 24


def test_digest_excludes_archived_messages(tmp_path) -> None:
    session.DB_PATH = tmp_path / "digest_archived.db"

    with TestClient(app) as client:
        _seed_event(client, "arch-1")
        resp = client.post("/api/v1/ingestion/messages/arch-1/archive?tenant_id=tenant_demo")
        assert resp.status_code == 200

        digest = _digest(client)
        assert digest["total"] == 0


def test_digest_is_tenant_scoped(tmp_path) -> None:
    session.DB_PATH = tmp_path / "digest_tenant_scoped.db"

    with TestClient(app) as client:
        _seed_event(client, "ta-1", tenant_id="tenant_a")
        _seed_event(client, "tb-1", tenant_id="tenant_b")

        digest_a = _digest(client, tenant_id="tenant_a")
        assert digest_a["total"] == 1

        digest_b = _digest(client, tenant_id="tenant_b")
        assert digest_b["total"] == 1


def test_digest_default_window_is_24_hours(tmp_path) -> None:
    session.DB_PATH = tmp_path / "digest_default_window.db"

    with TestClient(app) as client:
        digest = _digest(client)
        assert digest["since_hours"] == 24
