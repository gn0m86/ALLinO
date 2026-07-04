from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.main import app


def test_telegram_sync_endpoint_ingests_seeded_updates(tmp_path) -> None:
    session.DB_PATH = tmp_path / "telegram_sync.db"

    payload = {
        "seeded_updates": [
            {
                "update_id": 9001,
                "message": {
                    "message_id": 101,
                    "date": 1780000000,
                    "text": "Deploy failed in prod",
                    "chat": {"id": -100123, "title": "Ops Alerts"},
                    "from": {"username": "alerts_bot"},
                },
            },
            {
                "update_id": 9002,
                "message": {
                    "message_id": 102,
                    "date": 1780000060,
                    "text": "Rollback started",
                    "chat": {"id": -100123, "title": "Ops Alerts"},
                    "from": {"username": "alerts_bot"},
                },
            },
        ]
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/telegram/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "telegram" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "telegram"
    assert connectors[0]["status"] == "healthy"
