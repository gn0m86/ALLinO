from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.main import app


def test_slack_sync_endpoint_ingests_seeded_messages(tmp_path) -> None:
    session.DB_PATH = tmp_path / "slack_sync.db"

    payload = {
        "channel_id": "COPS",
        "seeded_messages": [
            {
                "ts": "1780000100.000200",
                "text": "Build failed on main",
                "user": "U123",
                "channel": "COPS",
            },
            {
                "ts": "1780000160.000500",
                "text": "Rollback started",
                "user": "U123",
                "channel": "COPS",
            },
        ],
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/slack/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "slack" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "slack"
    assert connectors[0]["status"] == "healthy"
