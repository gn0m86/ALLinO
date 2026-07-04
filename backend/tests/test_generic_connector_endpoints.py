from fastapi.testclient import TestClient

from app.db import session
from app.main import app


def _create_payload(name: str = "My Jenkins", webhook_enabled: bool = False) -> dict:
    return {
        "name": name,
        "base_url": "https://example.invalid/events",
        "auth_method": "none",
        "field_mapping": {"externalId": "id", "timestamp": "updated_at", "preview": "title"},
        "webhook_enabled": webhook_enabled,
    }


def test_create_list_and_delete_generic_connector(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_crud.db"

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
            json=_create_payload(),
        )
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert created["slug"] == "my-jenkins"
        assert created["tenant_id"] == "tenant_demo"
        assert created["webhook_url"] is None

        list_resp = client.get("/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        delete_resp = client.delete(
            f"/api/v1/ingestion/connectors/generic/{created['id']}?tenant_id=tenant_demo"
        )
        assert delete_resp.status_code == 200

        list_after = client.get("/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo")
        assert list_after.json() == []


def test_create_generic_connector_duplicate_slug_conflicts(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_dup.db"

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
            json=_create_payload("Same Name"),
        )
        assert first.status_code == 200

        second = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
            json=_create_payload("Same Name"),
        )
        assert second.status_code == 409


def test_create_generic_connector_requires_auth_header_name_for_api_key(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_apikey_validation.db"

    payload = _create_payload("Needs Header")
    payload["auth_method"] = "api_key"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
            json=payload,
        )
        assert resp.status_code == 422


def test_generic_connector_is_tenant_scoped(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_tenant_scope.db"

    with TestClient(app) as client:
        create_a = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_a",
            json=_create_payload("Tenant A Source"),
        )
        assert create_a.status_code == 200
        config_id = create_a.json()["id"]

        list_b = client.get("/api/v1/ingestion/connectors/generic?tenant_id=tenant_b")
        assert list_b.json() == []

        delete_from_b = client.delete(
            f"/api/v1/ingestion/connectors/generic/{config_id}?tenant_id=tenant_b"
        )
        assert delete_from_b.status_code == 404


def test_sync_generic_connector_with_seeded_items(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_sync.db"

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
            json=_create_payload("Sync Source"),
        )
        config_id = create_resp.json()["id"]

        sync_resp = client.post(
            f"/api/v1/ingestion/connectors/generic/{config_id}/sync?tenant_id=tenant_demo",
            json={
                "seeded_items": [
                    {"id": "1", "updated_at": "2026-07-01T12:00:00Z", "title": "hello"},
                    {"id": "2", "updated_at": "2026-07-01T12:05:00Z", "title": "world"},
                ]
            },
        )
        assert sync_resp.status_code == 200
        body = sync_resp.json()
        assert body["processed"] == 2
        assert body["inserted"] == 2

        inbox_resp = client.get("/api/v1/ingestion/inbox?tenant_id=tenant_demo")
        assert inbox_resp.status_code == 200
        sources = {item["source"] for item in inbox_resp.json()}
        assert "generic:sync-source" in sources

        connectors_resp = client.get("/api/v1/ingestion/connectors?tenant_id=tenant_demo")
        registry = {c["source_type"]: c for c in connectors_resp.json()}
        assert registry["generic:sync-source"]["status"] == "healthy"
        assert registry["generic:sync-source"]["last_inserted"] == 2


def test_sync_nonexistent_generic_connector_returns_404(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_sync_missing.db"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/connectors/generic/does-not-exist/sync?tenant_id=tenant_demo",
            json={},
        )
        assert resp.status_code == 404


def test_update_generic_connector_partial_field(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_update_partial.db"

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
            json=_create_payload("Editable Source"),
        )
        config_id = create_resp.json()["id"]

        update_resp = client.patch(
            f"/api/v1/ingestion/connectors/generic/{config_id}?tenant_id=tenant_demo",
            json={"base_url": "https://new.example.invalid/events"},
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["base_url"] == "https://new.example.invalid/events"
        assert updated["name"] == "Editable Source"
        assert updated["slug"] == "editable-source"
        assert updated["poll_interval_seconds"] is None

        list_resp = client.get("/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo")
        assert list_resp.json()[0]["base_url"] == "https://new.example.invalid/events"


def test_update_generic_connector_unknown_id_returns_404(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_update_missing.db"

    with TestClient(app) as client:
        resp = client.patch(
            "/api/v1/ingestion/connectors/generic/does-not-exist?tenant_id=tenant_demo",
            json={"base_url": "https://example.invalid"},
        )
        assert resp.status_code == 404


def test_update_generic_connector_requires_auth_header_name_for_api_key(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_update_apikey_validation.db"

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
            json=_create_payload("Needs Header On Update"),
        )
        config_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/ingestion/connectors/generic/{config_id}?tenant_id=tenant_demo",
            json={"auth_method": "api_key"},
        )
        assert resp.status_code == 422

        resp_ok = client.patch(
            f"/api/v1/ingestion/connectors/generic/{config_id}?tenant_id=tenant_demo",
            json={"auth_method": "api_key", "auth_header_name": "X-API-Key"},
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json()["auth_header_name"] == "X-API-Key"


def test_update_generic_connector_is_tenant_scoped(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_update_tenant_scope.db"

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_a",
            json=_create_payload("Tenant A Editable"),
        )
        config_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/ingestion/connectors/generic/{config_id}?tenant_id=tenant_b",
            json={"base_url": "https://example.invalid"},
        )
        assert resp.status_code == 404


def test_sync_generic_connector_failure_updates_registry_status(tmp_path) -> None:
    session.DB_PATH = tmp_path / "generic_connector_sync_failure.db"

    with TestClient(app) as client:
        payload = _create_payload("Unreachable Source")
        payload["base_url"] = "http://127.0.0.1:1/events"
        create_resp = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
            json=payload,
        )
        config_id = create_resp.json()["id"]

        sync_resp = client.post(
            f"/api/v1/ingestion/connectors/generic/{config_id}/sync?tenant_id=tenant_demo",
            json={"retry_max_attempts": 1, "retry_backoff_seconds": 0},
        )
        assert sync_resp.status_code == 502

        connectors_resp = client.get("/api/v1/ingestion/connectors?tenant_id=tenant_demo")
        registry = {c["source_type"]: c for c in connectors_resp.json()}
        assert registry["generic:unreachable-source"]["status"] == "error"
        assert registry["generic:unreachable-source"]["last_error"]
