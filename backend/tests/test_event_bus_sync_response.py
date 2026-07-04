from fastapi.testclient import TestClient

from app.db import session
from app.main import app


def test_connector_sync_response_contains_event_bus_mode(tmp_path) -> None:
    session.DB_PATH = tmp_path / "event_bus_sync_response.db"

    payload = {
        "seeded_notifications": [
            {
                "id": "gh-eb-1",
                "updated_at": "2026-07-01T12:00:00Z",
                "reason": "mention",
                "subject": {"title": "Issue mention", "type": "Issue"},
                "repository": {"full_name": "org/repo"},
            }
        ]
    }

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json=payload,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["event_bus"] in {"direct", "worker_async", "external_worker", "redis_stream", "redis_fallback"}
