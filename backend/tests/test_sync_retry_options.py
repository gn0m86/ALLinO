import httpx
from fastapi.testclient import TestClient

from app.connectors.teams_connector import TeamsConnector
from app.connectors.zoom_connector import ZoomConnector
from app.db import session
from app.main import app


def test_zoom_sync_retry_options_are_applied(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "zoom_retry_options.db"

    attempts = {"count": 0}

    def flaky_fetch(self: ZoomConnector) -> list[dict[str, str]]:
        attempts["count"] += 1
        if attempts["count"] < 5:
            request = httpx.Request("GET", "https://api.zoom.us/v2/users/me/meetings")
            response = httpx.Response(status_code=503, request=request)
            raise httpx.HTTPStatusError("service unavailable", request=request, response=response)
        return [
            {
                "id": "retry-z-1",
                "topic": "Recovered after retries",
                "start_time": "2026-07-01T11:30:00Z",
            }
        ]

    monkeypatch.setattr(ZoomConnector, "_fetch_meetings_from_api", flaky_fetch)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/zoom/sync?tenant_id=tenant_demo",
            headers={"X-Connector-Token": "zoom-token"},
            json={
                "retry_max_attempts": 5,
                "retry_backoff_seconds": 0.0,
            },
        )

    assert response.status_code == 200
    assert attempts["count"] == 5
    data = response.json()
    assert data["processed"] == 1
    assert data["inserted"] == 1


def test_teams_sync_retry_options_are_applied(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "teams_retry_options.db"

    attempts = {"count": 0}

    def flaky_fetch(self: TeamsConnector) -> list[dict[str, object]]:
        attempts["count"] += 1
        if attempts["count"] < 4:
            request = httpx.Request("GET", "https://graph.microsoft.com/v1.0/me/chats")
            response = httpx.Response(status_code=503, request=request)
            raise httpx.HTTPStatusError("service unavailable", request=request, response=response)
        return [
            {
                "id": "retry-t-1",
                "chatId": "chat-retry",
                "createdDateTime": "2026-07-01T13:00:00Z",
                "body": {"content": "Recovered after retries"},
            }
        ]

    monkeypatch.setattr(TeamsConnector, "_fetch_messages_from_api", flaky_fetch)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/teams/sync?tenant_id=tenant_demo",
            headers={"X-Connector-Token": "teams-token"},
            json={
                "retry_max_attempts": 4,
                "retry_backoff_seconds": 0.0,
            },
        )

    assert response.status_code == 200
    assert attempts["count"] == 4
    data = response.json()
    assert data["processed"] == 1
    assert data["inserted"] == 1


def test_sync_retry_options_validation_bounds(tmp_path) -> None:
    session.DB_PATH = tmp_path / "retry_options_validation.db"

    with TestClient(app) as client:
        bad_attempts = client.post(
            "/api/v1/ingestion/connectors/zoom/sync?tenant_id=tenant_demo",
            json={"retry_max_attempts": 0},
        )
        bad_backoff = client.post(
            "/api/v1/ingestion/connectors/teams/sync?tenant_id=tenant_demo",
            json={"retry_backoff_seconds": -0.1},
        )

    assert bad_attempts.status_code == 422
    assert bad_backoff.status_code == 422
