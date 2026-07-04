import httpx
from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.db.repositories.connector_runs_repo import list_connector_runs
from app.connectors.google_calendar_connector import GoogleCalendarConnector
from app.main import app


def test_google_calendar_sync_endpoint_ingests_seeded_events(tmp_path) -> None:
    session.DB_PATH = tmp_path / "google_calendar_sync.db"

    payload = {
        "seeded_events": [
            {
                "id": "evt-123",
                "summary": "Daily Incident Sync",
                "organizer": {"email": "ops@example.com"},
                "start": {"dateTime": "2026-07-01T11:30:00Z"},
            },
            {
                "id": "evt-124",
                "summary": "Postmortem Review",
                "organizer": {"email": "ops@example.com"},
                "start": {"dateTime": "2026-07-01T12:30:00Z"},
            },
        ],
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/google_calendar/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "google_calendar" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "google_calendar"
    assert connectors[0]["status"] == "healthy"


def test_google_calendar_sync_endpoint_failure_persists_error_state(tmp_path) -> None:
    session.DB_PATH = tmp_path / "google_calendar_sync_error.db"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/google_calendar/sync?tenant_id=tenant_demo",
            json={
                "cursor": "bad-cursor",
                "seeded_events": [
                    {
                        "id": "evt-500",
                        "summary": "Will fail before processing",
                        "start": {"dateTime": "2026-07-01T12:30:00Z"},
                    }
                ],
            },
        )
        assert response.status_code == 502

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "google_calendar"
    assert connectors[0]["status"] == "error"
    assert connectors[0]["last_error"]

    runs = list_connector_runs(tenant_id="tenant_demo", limit=5, source_type="google_calendar")
    assert runs
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]


def test_google_calendar_sync_endpoint_fail_fast_on_401(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "google_calendar_sync_401.db"

    attempts = {"count": 0}

    def unauthorized(self: GoogleCalendarConnector) -> list[dict[str, str]]:
        attempts["count"] += 1
        request = httpx.Request(
            "GET", "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        )
        response = httpx.Response(status_code=401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(GoogleCalendarConnector, "_fetch_events_from_api", unauthorized)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/google_calendar/sync?tenant_id=tenant_demo",
            headers={"X-Connector-Token": "bad-token"},
            json={},
        )
        assert response.status_code == 502

    assert attempts["count"] == 1

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "google_calendar"
    assert connectors[0]["status"] == "error"
    assert connectors[0]["last_error"]

    runs = list_connector_runs(tenant_id="tenant_demo", limit=5, source_type="google_calendar")
    assert runs
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]
