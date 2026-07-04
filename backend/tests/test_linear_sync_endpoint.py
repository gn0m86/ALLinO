from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.main import app


def test_linear_sync_endpoint_ingests_seeded_events(tmp_path) -> None:
    session.DB_PATH = tmp_path / "linear_sync.db"

    payload = {
        "seeded_events": [
            {
                "id": "lin-101",
                "identifier": "ENG-101",
                "title": "Fix search",
                "url": "https://linear.app/org/issue/ENG-101",
                "createdAt": "2026-06-25T12:00:00Z",
                "state": {"name": "Backlog"},
                "team": {"key": "ENG"},
            },
            {
                "id": "lin-102",
                "identifier": "ENG-102",
                "title": "Stabilize API",
                "url": "https://linear.app/org/issue/ENG-102",
                "createdAt": "2026-06-25T12:05:00Z",
                "state": {"name": "In Progress"},
                "team": {"key": "ENG"},
            },
        ]
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/linear/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "linear" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "linear"
    assert connectors[0]["status"] == "healthy"
