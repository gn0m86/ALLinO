from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.main import app


def test_github_sync_endpoint_ingests_seeded_notifications(tmp_path) -> None:
    session.DB_PATH = tmp_path / "github_sync.db"

    payload = {
        "seeded_notifications": [
            {
                "id": "gh-1",
                "updated_at": "2026-06-25T12:00:00Z",
                "reason": "review_requested",
                "subject": {"title": "Review PR #1", "type": "PullRequest"},
                "repository": {"full_name": "org/repo"},
            },
            {
                "id": "gh-2",
                "updated_at": "2026-06-25T12:05:00Z",
                "reason": "mention",
                "subject": {"title": "Issue mention", "type": "Issue"},
                "repository": {"full_name": "org/repo"},
            },
        ]
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "github" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "github"
    assert connectors[0]["status"] == "healthy"
