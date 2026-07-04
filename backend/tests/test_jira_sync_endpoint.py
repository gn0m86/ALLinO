from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.main import app


def test_jira_sync_endpoint_ingests_seeded_issues(tmp_path) -> None:
    session.DB_PATH = tmp_path / "jira_sync.db"

    payload = {
        "seeded_issues": [
            {
                "id": "10001",
                "key": "ENG-42",
                "fields": {
                    "summary": "Fix auth regression",
                    "updated": "2026-07-01T10:00:00Z",
                    "project": {"key": "ENG"},
                    "issuetype": {"name": "Bug"},
                },
            },
            {
                "id": "10002",
                "key": "ENG-43",
                "fields": {
                    "summary": "Improve retries",
                    "updated": "2026-07-01T10:05:00Z",
                    "project": {"key": "ENG"},
                    "issuetype": {"name": "Task"},
                },
            },
        ]
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/jira/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "jira" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "jira"
    assert connectors[0]["status"] == "healthy"
