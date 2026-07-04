import httpx
from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.db.repositories.connector_runs_repo import list_connector_runs
from app.connectors.teams_connector import TeamsConnector
from app.main import app


def test_teams_sync_endpoint_ingests_seeded_messages(tmp_path) -> None:
    session.DB_PATH = tmp_path / "teams_sync.db"

    payload = {
        "seeded_messages": [
            {
                "id": "msg-100",
                "chatId": "chat-1",
                "createdDateTime": "2026-07-01T13:00:00Z",
                "body": {"content": "prod deploy approved"},
                "from": {"user": {"displayName": "Ops Bot"}},
                "webUrl": "https://teams.microsoft.com/l/message/msg-100",
            },
            {
                "id": "msg-101",
                "chatId": "chat-1",
                "createdDateTime": "2026-07-01T13:05:00Z",
                "body": {"content": "rollback plan ready"},
                "from": {"user": {"displayName": "Ops Bot"}},
                "webUrl": "https://teams.microsoft.com/l/message/msg-101",
            },
        ]
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/teams/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "teams" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "teams"
    assert connectors[0]["status"] == "healthy"


def test_teams_sync_endpoint_failure_persists_error_state(tmp_path) -> None:
    session.DB_PATH = tmp_path / "teams_sync_error.db"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/teams/sync?tenant_id=tenant_demo",
            json={
                "cursor": "bad-cursor",
                "seeded_messages": [
                    {
                        "id": "msg-err-1",
                        "chatId": "chat-err",
                        "createdDateTime": "2026-07-01T13:00:00Z",
                        "body": {"content": "will fail"},
                    }
                ],
            },
        )
        assert response.status_code == 502

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "teams"
    assert connectors[0]["status"] == "error"
    assert connectors[0]["last_error"]

    runs = list_connector_runs(tenant_id="tenant_demo", limit=5, source_type="teams")
    assert runs
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]


def test_teams_sync_endpoint_fail_fast_on_401(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "teams_sync_401.db"

    attempts = {"count": 0}

    def unauthorized(self: TeamsConnector) -> list[dict[str, str]]:
        attempts["count"] += 1
        request = httpx.Request("GET", "https://graph.microsoft.com/v1.0/me/chats")
        response = httpx.Response(status_code=401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(TeamsConnector, "_fetch_messages_from_api", unauthorized)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/teams/sync?tenant_id=tenant_demo",
            headers={"X-Connector-Token": "bad-token"},
            json={},
        )
        assert response.status_code == 502

    assert attempts["count"] == 1

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "teams"
    assert connectors[0]["status"] == "error"
    assert connectors[0]["last_error"]

    runs = list_connector_runs(tenant_id="tenant_demo", limit=5, source_type="teams")
    assert runs
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]
