from fastapi.testclient import TestClient

from app.db import session
from app.db.repositories.connectors_repo import list_connectors
from app.main import app


def test_gitlab_sync_endpoint_ingests_seeded_notifications(tmp_path) -> None:
    session.DB_PATH = tmp_path / "gitlab_sync.db"

    payload = {
        "seeded_notifications": [
            {
                "id": 101,
                "created_at": "2026-06-25T12:00:00Z",
                "action_name": "mentioned",
                "target_title": "Fix pipeline",
                "target_type": "MergeRequest",
                "target_url": "https://gitlab.com/org/repo/-/merge_requests/7",
                "project": {"path_with_namespace": "org/repo"},
            },
            {
                "id": 102,
                "created_at": "2026-06-25T12:05:00Z",
                "action_name": "approved",
                "target_title": "Release prep",
                "target_type": "MergeRequest",
                "target_url": "https://gitlab.com/org/repo/-/merge_requests/8",
                "project": {"path_with_namespace": "org/repo"},
            },
        ]
    }

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/v1/ingestion/connectors/gitlab/sync?tenant_id=tenant_demo",
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
        assert all(item["source"] == "gitlab" for item in inbox_items)

    connectors = list_connectors("tenant_demo")
    assert len(connectors) == 1
    assert connectors[0]["source_type"] == "gitlab"
    assert connectors[0]["status"] == "healthy"
