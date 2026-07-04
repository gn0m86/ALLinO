import httpx
from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.db.repositories.connector_runs_repo import list_connector_runs
from app.connectors.rocketchat_connector import RocketChatConnector
from app.main import app


def test_rocketchat_sync_endpoint_ingests_seeded_messages(tmp_path) -> None:
    session.DB_PATH = tmp_path / "rocketchat_sync.db"

    payload = {
        "channel_id": "GENERAL",
        "seeded_messages": [
            {
                "_id": "3001",
                "ts": "2026-07-02T12:10:00Z",
                "msg": "deploy finished",
                "rid": "GENERAL",
                "u": {"username": "ops-bot"},
            },
            {
                "_id": "3002",
                "ts": "2026-07-02T12:12:00Z",
                "msg": "incident acknowledged",
                "rid": "GENERAL",
                "u": {"username": "ops-bot"},
            },
        ],
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/rocketchat/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "rocketchat" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "rocketchat"
    assert connectors[0]["status"] == "healthy"


def test_rocketchat_sync_endpoint_failure_persists_error_state(tmp_path) -> None:
    session.DB_PATH = tmp_path / "rocketchat_sync_error.db"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/rocketchat/sync?tenant_id=tenant_demo",
            json={
                "cursor": "bad-cursor",
                "seeded_messages": [
                    {
                        "_id": "3500",
                        "msg": "will fail before processing",
                        "ts": "2026-07-02T12:30:00Z",
                        "rid": "GENERAL",
                    }
                ],
            },
        )
        assert response.status_code == 502

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "rocketchat"
    assert connectors[0]["status"] == "error"
    assert connectors[0]["last_error"]

    runs = list_connector_runs(tenant_id="tenant_demo", limit=5, source_type="rocketchat")
    assert runs
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]


def test_rocketchat_sync_endpoint_fail_fast_on_401(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "rocketchat_sync_401.db"
    monkeypatch.setenv("ALLINO_ROCKETCHAT_USER_ID", "rc-user-401")

    attempts = {"count": 0}

    def unauthorized(self: RocketChatConnector) -> list[dict[str, str]]:
        attempts["count"] += 1
        request = httpx.Request("GET", "https://chat.example.com/api/v1/channels.messages")
        response = httpx.Response(status_code=401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(RocketChatConnector, "_fetch_messages_from_api", unauthorized)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/rocketchat/sync?tenant_id=tenant_demo",
            headers={"X-Connector-Token": "bad-token"},
            json={"channel_id": "GENERAL", "base_url": "https://chat.example.com"},
        )
        assert response.status_code == 502

    assert attempts["count"] == 1

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "rocketchat"
    assert connectors[0]["status"] == "error"
    assert connectors[0]["last_error"]

    runs = list_connector_runs(tenant_id="tenant_demo", limit=5, source_type="rocketchat")
    assert runs
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]
