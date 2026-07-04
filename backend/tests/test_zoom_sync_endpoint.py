import httpx
from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.db.repositories.connector_runs_repo import list_connector_runs
from app.connectors.zoom_connector import ZoomConnector
from app.main import app


def test_zoom_sync_endpoint_ingests_seeded_events(tmp_path) -> None:
    session.DB_PATH = tmp_path / "zoom_sync.db"

    payload = {
        "seeded_events": [
            {
                "id": "823456",
                "uuid": "uuid-1",
                "topic": "Daily Incident Sync",
                "host_email": "ops@example.com",
                "start_time": "2026-07-01T11:30:00Z",
                "join_url": "https://zoom.us/j/823456",
            },
            {
                "id": "823457",
                "uuid": "uuid-2",
                "topic": "Postmortem Review",
                "host_email": "ops@example.com",
                "start_time": "2026-07-01T12:30:00Z",
                "join_url": "https://zoom.us/j/823457",
            },
        ],
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/zoom/sync?tenant_id=tenant_demo",
            json=payload,
        )

        assert sync_response.status_code == 200
        data = sync_response.json()
        assert data["processed"] == 2
        assert data["inserted"] == 2
        assert data["duplicates"] == 0
        assert data["rejected"] == 0

        inbox_response = client.get(
            "/api/v1/ingestion/inbox?tenant_id=tenant_demo&limit=10"
        )
        assert inbox_response.status_code == 200
        inbox_items = inbox_response.json()
        assert len(inbox_items) == 2
        assert all(item["source"] == "zoom" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "zoom"
    assert connectors[0]["status"] == "healthy"


def test_zoom_sync_endpoint_failure_persists_error_state(tmp_path) -> None:
    session.DB_PATH = tmp_path / "zoom_sync_error.db"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/zoom/sync?tenant_id=tenant_demo",
            json={
                "cursor": "bad-cursor",
                "seeded_events": [
                    {
                        "id": "823500",
                        "topic": "Will fail before processing",
                        "start_time": "2026-07-01T12:30:00Z",
                    }
                ],
            },
        )
        assert response.status_code == 502

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "zoom"
    assert connectors[0]["status"] == "error"
    assert connectors[0]["last_error"]

    runs = list_connector_runs(tenant_id="tenant_demo", limit=5, source_type="zoom")
    assert runs
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]


def test_zoom_sync_endpoint_fail_fast_on_401(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "zoom_sync_401.db"

    attempts = {"count": 0}

    def unauthorized(self: ZoomConnector) -> list[dict[str, str]]:
        attempts["count"] += 1
        request = httpx.Request("GET", "https://api.zoom.us/v2/users/me/meetings")
        response = httpx.Response(status_code=401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(ZoomConnector, "_fetch_meetings_from_api", unauthorized)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/zoom/sync?tenant_id=tenant_demo",
            headers={"X-Connector-Token": "bad-token"},
            json={},
        )
        assert response.status_code == 502

    assert attempts["count"] == 1

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "zoom"
    assert connectors[0]["status"] == "error"
    assert connectors[0]["last_error"]

    runs = list_connector_runs(tenant_id="tenant_demo", limit=5, source_type="zoom")
    assert runs
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]
