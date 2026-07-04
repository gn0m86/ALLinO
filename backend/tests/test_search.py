from fastapi.testclient import TestClient

from app.db import session
from app.main import app


def _seed_event(client: TestClient, event_id: str, preview: str, tenant_id: str = "tenant_demo") -> None:
    resp = client.post(
        f"/api/v1/ingestion/events?tenant_id={tenant_id}",
        json={
            "eventId": event_id,
            "tenantId": tenant_id,
            "sourceType": "github",
            "externalId": event_id,
            "timestamp": "2026-07-03T12:00:00Z",
            "payload": {"text": preview},
            "schemaVersion": "1.0.0",
        },
    )
    assert resp.status_code == 200


def _search(client: TestClient, q: str, tenant_id: str = "tenant_demo") -> list[dict]:
    resp = client.get(f"/api/v1/ingestion/search?tenant_id={tenant_id}&q={q}")
    assert resp.status_code == 200
    return resp.json()


def test_search_matches_preview_text(tmp_path) -> None:
    session.DB_PATH = tmp_path / "search_preview.db"

    with TestClient(app) as client:
        _seed_event(client, "s1", "database migration failed on staging")
        _seed_event(client, "s2", "deploy succeeded")

        results = _search(client, "migration")
        assert [r["event_id"] for r in results] == ["s1"]


def test_search_matches_external_id(tmp_path) -> None:
    session.DB_PATH = tmp_path / "search_external_id.db"

    with TestClient(app) as client:
        _seed_event(client, "pr-4821", "reviewed and approved")

        results = _search(client, "4821")
        assert [r["event_id"] for r in results] == ["pr-4821"]


def test_search_is_case_insensitive(tmp_path) -> None:
    session.DB_PATH = tmp_path / "search_case.db"

    with TestClient(app) as client:
        _seed_event(client, "s3", "Rate Limit Exceeded")

        results = _search(client, "rate limit")
        assert [r["event_id"] for r in results] == ["s3"]


def test_search_no_matches_returns_empty_list(tmp_path) -> None:
    session.DB_PATH = tmp_path / "search_empty.db"

    with TestClient(app) as client:
        _seed_event(client, "s4", "everything is fine")

        assert _search(client, "nonexistent-keyword-xyz") == []


def test_search_excludes_archived_messages(tmp_path) -> None:
    session.DB_PATH = tmp_path / "search_excludes_archived.db"

    with TestClient(app) as client:
        _seed_event(client, "s5", "quarterly report attached")
        assert [r["event_id"] for r in _search(client, "quarterly")] == ["s5"]

        resp = client.post("/api/v1/ingestion/messages/s5/archive?tenant_id=tenant_demo")
        assert resp.status_code == 200

        assert _search(client, "quarterly") == []


def test_search_is_tenant_scoped(tmp_path) -> None:
    session.DB_PATH = tmp_path / "search_tenant_scoped.db"

    with TestClient(app) as client:
        _seed_event(client, "s6", "shared keyword here", tenant_id="tenant_a")
        _seed_event(client, "s7", "shared keyword here", tenant_id="tenant_b")

        results_a = _search(client, "shared", tenant_id="tenant_a")
        assert [r["event_id"] for r in results_a] == ["s6"]

        results_b = _search(client, "shared", tenant_id="tenant_b")
        assert [r["event_id"] for r in results_b] == ["s7"]


def test_search_respects_limit(tmp_path) -> None:
    session.DB_PATH = tmp_path / "search_limit.db"

    with TestClient(app) as client:
        for i in range(5):
            _seed_event(client, f"lim-{i}", "limit-test keyword")

        resp = client.get("/api/v1/ingestion/search?tenant_id=tenant_demo&q=limit-test&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


def test_search_requires_nonempty_query(tmp_path) -> None:
    session.DB_PATH = tmp_path / "search_empty_query.db"

    with TestClient(app) as client:
        resp = client.get("/api/v1/ingestion/search?tenant_id=tenant_demo&q=")
        assert resp.status_code == 422
