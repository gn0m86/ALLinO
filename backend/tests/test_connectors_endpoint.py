from fastapi.testclient import TestClient

from app.db import session
from app.main import app


def _seeded_notification(notification_id: str) -> dict:
    return {
        "id": notification_id,
        "updated_at": "2026-06-25T12:00:00Z",
        "reason": "mention",
        "subject": {"title": "Issue mention", "type": "Issue"},
        "repository": {"full_name": "org/repo"},
    }


def test_connectors_endpoint_returns_registered_connectors_for_tenant(tmp_path) -> None:
    session.DB_PATH = tmp_path / "connectors_endpoint.db"

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={"seeded_notifications": [_seeded_notification("gh-conn-1")]},
        )
        assert sync_response.status_code == 200

        connectors_response = client.get("/api/v1/ingestion/connectors?tenant_id=tenant_demo")
        assert connectors_response.status_code == 200
        connectors = connectors_response.json()

    assert len(connectors) == 1
    assert connectors[0]["tenant_id"] == "tenant_demo"
    assert connectors[0]["source_type"] == "github"
    assert connectors[0]["status"] == "healthy"
    assert connectors[0]["last_error"] is None
    assert connectors[0]["last_synced_at"] is not None
    assert connectors[0]["last_processed"] == 1
    assert connectors[0]["last_inserted"] == 1
    assert connectors[0]["last_duplicates"] == 0
    assert connectors[0]["last_rejected"] == 0


def test_connectors_endpoint_is_tenant_scoped(tmp_path) -> None:
    session.DB_PATH = tmp_path / "connectors_tenant_scope.db"

    with TestClient(app) as client:
        r1 = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_a",
            json={"seeded_notifications": [_seeded_notification("gh-a-1")]},
        )
        assert r1.status_code == 200

        r2 = client.post(
            "/api/v1/ingestion/connectors/linear/sync?tenant_id=tenant_b",
            json={
                "seeded_events": [
                    {
                        "id": "lin-b-1",
                        "identifier": "ENG-1",
                        "title": "Tenant B issue",
                        "url": "https://linear.app/org/issue/ENG-1",
                        "createdAt": "2026-06-25T12:05:00Z",
                        "state": {"name": "Backlog"},
                        "team": {"key": "ENG"},
                    }
                ]
            },
        )
        assert r2.status_code == 200

        c_a = client.get("/api/v1/ingestion/connectors?tenant_id=tenant_a")
        c_b = client.get("/api/v1/ingestion/connectors?tenant_id=tenant_b")
        assert c_a.status_code == 200
        assert c_b.status_code == 200

    connectors_a = c_a.json()
    connectors_b = c_b.json()
    assert len(connectors_a) == 1
    assert len(connectors_b) == 1
    assert connectors_a[0]["source_type"] == "github"
    assert connectors_b[0]["source_type"] == "linear"


def test_connector_sync_failure_updates_registry_status(tmp_path) -> None:
    session.DB_PATH = tmp_path / "connectors_failure_state.db"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={
                "cursor": "bad-cursor",
                "seeded_notifications": [_seeded_notification("gh-bad-cursor")],
            },
        )
        assert response.status_code == 502

        connectors_response = client.get("/api/v1/ingestion/connectors?tenant_id=tenant_demo")
        assert connectors_response.status_code == 200
        connectors = connectors_response.json()

    assert len(connectors) == 1
    row = connectors[0]
    assert row["source_type"] == "github"
    assert row["status"] == "error"
    assert row["last_error"]
    assert row["last_processed"] == 0
    assert row["last_inserted"] == 0
    assert row["last_duplicates"] == 0
    assert row["last_rejected"] == 0
