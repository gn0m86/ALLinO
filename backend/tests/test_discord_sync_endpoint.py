from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.main import app


def test_discord_sync_endpoint_ingests_seeded_messages(tmp_path) -> None:
    session.DB_PATH = tmp_path / "discord_sync.db"

    payload = {
        "channel_id": "987",
        "seeded_messages": [
            {
                "id": "2001",
                "timestamp": "2026-07-01T12:10:00Z",
                "content": "API latency spike",
                "channel_id": "987",
                "author": {"username": "ops-bot"},
            },
            {
                "id": "2002",
                "timestamp": "2026-07-01T12:12:00Z",
                "content": "incident acknowledged",
                "channel_id": "987",
                "author": {"username": "ops-bot"},
            },
        ],
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/discord/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "discord" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "discord"
    assert connectors[0]["status"] == "healthy"
