import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.db import session
from app.main import app


def _sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _create_webhook_connector(client: TestClient, tenant_id: str = "tenant_demo") -> dict:
    resp = client.post(
        f"/api/v1/ingestion/connectors/generic?tenant_id={tenant_id}",
        json={
            "name": "Webhook Source",
            "field_mapping": {"externalId": "id", "timestamp": "updated_at", "preview": "title"},
            "webhook_enabled": True,
        },
    )
    assert resp.status_code == 200
    return resp.json()


def test_webhook_rejected_when_secret_not_configured(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "webhook_no_secret.db"
    monkeypatch.delenv("ALLINO_GENERIC_WEBHOOK_SOURCE_WEBHOOK_SECRET", raising=False)

    with TestClient(app) as client:
        config = _create_webhook_connector(client)
        body = json.dumps({"id": "1", "updated_at": "2026-07-01T12:00:00Z", "title": "hi"}).encode()

        resp = client.post(
            f"/webhooks/{config['id']}",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 503


def test_webhook_rejected_with_invalid_signature(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "webhook_bad_sig.db"
    monkeypatch.setenv("ALLINO_GENERIC_WEBHOOK_SOURCE_WEBHOOK_SECRET", "s3cr3t")

    with TestClient(app) as client:
        config = _create_webhook_connector(client)
        body = json.dumps({"id": "1", "updated_at": "2026-07-01T12:00:00Z", "title": "hi"}).encode()

        resp = client.post(
            f"/webhooks/{config['id']}",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": "sha256=deadbeef"},
        )
        assert resp.status_code == 401


def test_webhook_rejected_with_missing_signature(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "webhook_missing_sig.db"
    monkeypatch.setenv("ALLINO_GENERIC_WEBHOOK_SOURCE_WEBHOOK_SECRET", "s3cr3t")

    with TestClient(app) as client:
        config = _create_webhook_connector(client)
        body = json.dumps({"id": "1", "updated_at": "2026-07-01T12:00:00Z", "title": "hi"}).encode()

        resp = client.post(
            f"/webhooks/{config['id']}",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401


def test_webhook_accepted_with_valid_signature_single_object(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "webhook_valid_single.db"
    secret = "s3cr3t"
    monkeypatch.setenv("ALLINO_GENERIC_WEBHOOK_SOURCE_WEBHOOK_SECRET", secret)

    with TestClient(app) as client:
        config = _create_webhook_connector(client)
        body = json.dumps({"id": "1", "updated_at": "2026-07-01T12:00:00Z", "title": "hi"}).encode()

        resp = client.post(
            f"/webhooks/{config['id']}",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": _sign(secret, body)},
        )
        assert resp.status_code == 200
        assert resp.json()["inserted"] == 1

        inbox = client.get("/api/v1/ingestion/inbox?tenant_id=tenant_demo")
        sources = {item["source"] for item in inbox.json()}
        assert "generic:webhook-source" in sources


def test_webhook_accepted_with_valid_signature_array_batch(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "webhook_valid_batch.db"
    secret = "s3cr3t"
    monkeypatch.setenv("ALLINO_GENERIC_WEBHOOK_SOURCE_WEBHOOK_SECRET", secret)

    with TestClient(app) as client:
        config = _create_webhook_connector(client)
        body = json.dumps(
            {
                "items": [
                    {"id": "1", "updated_at": "2026-07-01T12:00:00Z", "title": "a"},
                    {"id": "2", "updated_at": "2026-07-01T12:05:00Z", "title": "b"},
                ]
            }
        ).encode()

        resp = client.post(
            f"/webhooks/{config['id']}",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": _sign(secret, body)},
        )
        assert resp.status_code == 200
        assert resp.json()["processed"] == 2
        assert resp.json()["inserted"] == 2


def test_webhook_unknown_connector_id_returns_404(tmp_path) -> None:
    session.DB_PATH = tmp_path / "webhook_unknown.db"

    with TestClient(app) as client:
        resp = client.post("/webhooks/does-not-exist", content=b"{}")
        assert resp.status_code == 404


def test_webhook_disabled_connector_returns_404(tmp_path) -> None:
    session.DB_PATH = tmp_path / "webhook_disabled.db"

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
            json={
                "name": "No Webhook",
                "base_url": "https://example.invalid",
                "field_mapping": {"externalId": "id", "timestamp": "updated_at"},
                "webhook_enabled": False,
            },
        )
        config_id = create_resp.json()["id"]

        resp = client.post(f"/webhooks/{config_id}", content=b"{}")
        assert resp.status_code == 404


def test_webhook_dedupes_against_poll_sync_of_same_external_id(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "webhook_dedup.db"
    secret = "s3cr3t"
    monkeypatch.setenv("ALLINO_GENERIC_WEBHOOK_SOURCE_WEBHOOK_SECRET", secret)

    with TestClient(app) as client:
        config = _create_webhook_connector(client)

        sync_resp = client.post(
            f"/api/v1/ingestion/connectors/generic/{config['id']}/sync?tenant_id=tenant_demo",
            json={"seeded_items": [{"id": "1", "updated_at": "2026-07-01T12:00:00Z", "title": "hi"}]},
        )
        assert sync_resp.json()["inserted"] == 1

        body = json.dumps({"id": "1", "updated_at": "2026-07-01T12:00:00Z", "title": "hi"}).encode()
        webhook_resp = client.post(
            f"/webhooks/{config['id']}",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": _sign(secret, body)},
        )
        assert webhook_resp.status_code == 200
        assert webhook_resp.json()["duplicates"] == 1
        assert webhook_resp.json()["inserted"] == 0
