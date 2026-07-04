from fastapi.testclient import TestClient

from app.db import session
from app.main import app


def _notification(notification_id: str) -> dict:
    return {
        "id": notification_id,
        "updated_at": "2026-06-25T12:00:00Z",
        "reason": "mention",
        "subject": {"title": "Issue mention", "type": "Issue"},
        "repository": {"full_name": "org/repo"},
    }


def test_connector_runs_endpoint_returns_recent_runs(tmp_path) -> None:
    session.DB_PATH = tmp_path / "connector_runs.db"

    with TestClient(app) as client:
        r1 = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={"seeded_notifications": [_notification("gh-run-1")]},
        )
        assert r1.status_code == 200

        runs_response = client.get(
            "/api/v1/ingestion/connectors/runs?tenant_id=tenant_demo&limit=10"
        )
        assert runs_response.status_code == 200
        runs = runs_response.json()

    assert len(runs) >= 1
    first = runs[0]
    assert first["tenant_id"] == "tenant_demo"
    assert first["source_type"] == "github"
    assert first["status"] in {"healthy", "degraded", "starting", "stopped", "error"}
    assert first["processed"] == 1
    assert first["inserted"] == 1


def test_connector_runs_endpoint_supports_source_filter(tmp_path) -> None:
    session.DB_PATH = tmp_path / "connector_runs_filter.db"

    with TestClient(app) as client:
        r1 = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={"seeded_notifications": [_notification("gh-run-filter")]},
        )
        assert r1.status_code == 200

        r2 = client.post(
            "/api/v1/ingestion/connectors/linear/sync?tenant_id=tenant_demo",
            json={
                "seeded_events": [
                    {
                        "id": "lin-run-filter",
                        "identifier": "ENG-42",
                        "title": "Linear event",
                        "url": "https://linear.app/org/issue/ENG-42",
                        "createdAt": "2026-06-25T12:05:00Z",
                        "state": {"name": "Backlog"},
                        "team": {"key": "ENG"},
                    }
                ]
            },
        )
        assert r2.status_code == 200

        filtered = client.get(
            "/api/v1/ingestion/connectors/runs?tenant_id=tenant_demo&source=github&limit=10"
        )
        assert filtered.status_code == 200
        rows = filtered.json()

    assert rows
    assert all(row["source_type"] == "github" for row in rows)


def test_connector_runs_endpoint_contains_error_runs(tmp_path) -> None:
    session.DB_PATH = tmp_path / "connector_runs_error.db"

    with TestClient(app) as client:
        failed = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={
                "cursor": "bad-cursor",
                "seeded_notifications": [_notification("gh-run-error")],
            },
        )
        assert failed.status_code == 502

        runs_response = client.get(
            "/api/v1/ingestion/connectors/runs?tenant_id=tenant_demo&limit=10"
        )
        assert runs_response.status_code == 200
        runs = runs_response.json()

    assert runs
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]
