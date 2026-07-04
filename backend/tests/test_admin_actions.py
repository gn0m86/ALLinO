import json

import pyotp
from fastapi.testclient import TestClient

from app.core import security
from app.db import session
from app.db.repositories.messages_repo import snooze_message
from app.main import app

TOTP_SECRET = "JBSWY3DPEHPK3PXP"


def _totp_code(secret: str = TOTP_SECRET) -> str:
    return pyotp.TOTP(secret).now()


def _seed_event(client: TestClient, event_id: str, tenant_id: str = "tenant_demo") -> None:
    resp = client.post(
        f"/api/v1/ingestion/events?tenant_id={tenant_id}",
        json={
            "eventId": event_id,
            "tenantId": tenant_id,
            "sourceType": "github",
            "externalId": event_id,
            "timestamp": "2026-07-03T12:00:00Z",
            "payload": {"text": "something happened"},
            "schemaVersion": "1.0.0",
        },
    )
    assert resp.status_code == 200


def _inbox_ids(client: TestClient, tenant_id: str = "tenant_demo") -> set[str]:
    resp = client.get(f"/api/v1/ingestion/inbox?tenant_id={tenant_id}")
    assert resp.status_code == 200
    return {item["event_id"] for item in resp.json()}


def _export_request(
    client: TestClient,
    tenant_id: str = "tenant_demo",
    totp_code: str | None = None,
    headers: dict | None = None,
):
    request_headers = dict(headers or {})
    if totp_code is not None:
        request_headers["X-TOTP-Code"] = totp_code
    return client.get(
        f"/api/v1/admin/tenant/audit/export?tenant_id={tenant_id}",
        headers=request_headers,
    )


def _rotate_request(
    client: TestClient,
    tenant_id: str = "tenant_demo",
    totp_code: str | None = None,
    headers: dict | None = None,
):
    request_headers = dict(headers or {})
    if totp_code is not None:
        request_headers["X-TOTP-Code"] = totp_code
    return client.post(
        f"/api/v1/admin/api-key/rotate?tenant_id={tenant_id}",
        headers=request_headers,
    )


def _delete_request(
    client: TestClient,
    tenant_id: str = "tenant_demo",
    confirm_tenant_id: str | None = None,
    totp_code: str | None = None,
    headers: dict | None = None,
):
    request_headers = dict(headers or {})
    if totp_code is not None:
        request_headers["X-TOTP-Code"] = totp_code
    return client.post(
        f"/api/v1/admin/tenant/messages/delete?tenant_id={tenant_id}",
        json={"confirm_tenant_id": confirm_tenant_id if confirm_tenant_id is not None else tenant_id},
        headers=request_headers,
    )


def test_delete_fails_without_totp_secret_configured(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_no_secret.db"
    monkeypatch.delenv("ALLINO_ADMIN_TOTP_SECRET", raising=False)

    with TestClient(app) as client:
        resp = _delete_request(client, totp_code="123456")
        assert resp.status_code == 503


def test_delete_fails_without_totp_header(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_no_header.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        resp = _delete_request(client)
        assert resp.status_code == 401


def test_delete_fails_with_wrong_totp_code(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_wrong_code.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        _seed_event(client, "wrong-code-guard")
        resp = _delete_request(client, totp_code="000000")
        assert resp.status_code == 403
        # Message must survive a rejected attempt.
        assert "wrong-code-guard" in _inbox_ids(client)


def test_delete_fails_when_confirm_tenant_id_mismatches(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_mismatch.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        _seed_event(client, "confirm-mismatch-guard")
        resp = _delete_request(client, confirm_tenant_id="not-the-right-tenant", totp_code=_totp_code())
        assert resp.status_code == 400
        assert "confirm-mismatch-guard" in _inbox_ids(client)


def test_delete_succeeds_removes_every_message_state_and_is_audited(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_delete_success.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        _seed_event(client, "active-1")
        _seed_event(client, "archived-1")
        _seed_event(client, "snoozed-1")

        resp = client.post("/api/v1/ingestion/messages/archived-1/archive?tenant_id=tenant_demo")
        assert resp.status_code == 200
        snooze_message(
            tenant_id="tenant_demo", event_id="snoozed-1", snoozed_until="2099-01-01T00:00:00+00:00"
        )

        resp = _delete_request(client, totp_code=_totp_code())
        assert resp.status_code == 200
        assert resp.json() == {"status": "deleted", "deleted_count": 3}

        assert _inbox_ids(client) == set()
        resp = client.get("/api/v1/ingestion/inbox?tenant_id=tenant_demo&archived=true")
        assert resp.json() == []

        audit = client.get("/api/v1/ingestion/audit?tenant_id=tenant_demo").json()
        matching = [e for e in audit if e["action"] == "admin.tenant_messages.deleted"]
        assert len(matching) == 1
        assert json.loads(matching[0]["metadata"])["deleted_count"] == 3


def test_delete_is_tenant_scoped(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_tenant_scoped.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        _seed_event(client, "a1", tenant_id="tenant_a")
        _seed_event(client, "b1", tenant_id="tenant_b")

        resp = _delete_request(client, tenant_id="tenant_a", totp_code=_totp_code())
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 1

        assert _inbox_ids(client, tenant_id="tenant_a") == set()
        assert "b1" in _inbox_ids(client, tenant_id="tenant_b")


def test_delete_allowed_for_jwt_admin_role_with_valid_totp(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_jwt_allowed.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        _seed_event(client, "jwt-admin-1")

    import jwt as pyjwt

    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_ADMIN_ROLES", {"admin"})
    monkeypatch.setattr(security, "ALLINO_JWT_ADMIN_SCOPES", {"admin:destructive"})

    token = pyjwt.encode(
        {"sub": "admin-user", "role": "admin", "tenant_id": "tenant_demo"},
        "jwt-secret",
        algorithm="HS256",
    )

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/admin/tenant/messages/delete?tenant_id=tenant_demo",
            json={"confirm_tenant_id": "tenant_demo"},
            headers={"Authorization": f"Bearer {token}", "X-TOTP-Code": _totp_code()},
        )
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 1


def test_delete_forbidden_for_jwt_without_admin_role_even_with_valid_totp(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_jwt_forbidden.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    import jwt as pyjwt

    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_ADMIN_ROLES", {"admin"})
    monkeypatch.setattr(security, "ALLINO_JWT_ADMIN_SCOPES", {"admin:destructive"})

    token = pyjwt.encode(
        {"sub": "regular-user", "role": "operator", "tenant_id": "tenant_demo"},
        "jwt-secret",
        algorithm="HS256",
    )

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/admin/tenant/messages/delete?tenant_id=tenant_demo",
            json={"confirm_tenant_id": "tenant_demo"},
            headers={"Authorization": f"Bearer {token}", "X-TOTP-Code": _totp_code()},
        )
        assert resp.status_code == 403


def test_delete_requires_totp_even_for_trusted_api_key(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_api_key_still_needs_totp.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    # Seed under the default insecure-dev conftest state, before locking the
    # security module down to API-key-only auth below.
    with TestClient(app) as client:
        _seed_event(client, "api-key-guard")

    monkeypatch.setattr(security, "ALLINO_API_KEY", "trusted-master-key")

    with TestClient(app) as client:

        # A fully-trusted API key alone is NOT enough for this tier -- unlike
        # every other permission tier in this app.
        resp = client.post(
            "/api/v1/admin/tenant/messages/delete?tenant_id=tenant_demo",
            json={"confirm_tenant_id": "tenant_demo"},
            headers={"X-API-Key": "trusted-master-key"},
        )
        assert resp.status_code == 401

        resp = client.post(
            "/api/v1/admin/tenant/messages/delete?tenant_id=tenant_demo",
            json={"confirm_tenant_id": "tenant_demo"},
            headers={"X-API-Key": "trusted-master-key", "X-TOTP-Code": "000000"},
        )
        assert resp.status_code == 403

        resp = client.post(
            "/api/v1/admin/tenant/messages/delete?tenant_id=tenant_demo",
            json={"confirm_tenant_id": "tenant_demo"},
            headers={"X-API-Key": "trusted-master-key", "X-TOTP-Code": _totp_code()},
        )
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 1


def test_export_fails_without_totp_secret_configured(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_export_no_secret.db"
    monkeypatch.delenv("ALLINO_ADMIN_TOTP_SECRET", raising=False)

    with TestClient(app) as client:
        resp = _export_request(client, totp_code="123456")
        assert resp.status_code == 503


def test_export_fails_without_totp_header(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_export_no_header.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        resp = _export_request(client)
        assert resp.status_code == 401


def test_export_fails_with_wrong_totp_code(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_export_wrong_code.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        _seed_event(client, "export-wrong-code-guard")
        resp = _export_request(client, totp_code="000000")
        assert resp.status_code == 403


def test_export_succeeds_returns_entries_and_is_audited(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_export_success.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        _seed_event(client, "export-1")
        _seed_event(client, "export-2")

        resp = _export_request(client, totp_code=_totp_code())
        assert resp.status_code == 200
        body = resp.json()
        assert body["tenant_id"] == "tenant_demo"
        assert body["exported_count"] >= 2
        assert len(body["entries"]) == body["exported_count"]
        actions = {e["action"] for e in body["entries"]}
        assert "ingestion.event" in actions

        audit = client.get("/api/v1/ingestion/audit?tenant_id=tenant_demo").json()
        matching = [e for e in audit if e["action"] == "admin.tenant_audit.exported"]
        assert len(matching) == 1
        assert json.loads(matching[0]["metadata"])["exported_count"] == body["exported_count"]


def test_export_is_tenant_scoped(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_export_tenant_scoped.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        _seed_event(client, "a1", tenant_id="tenant_a")
        _seed_event(client, "b1", tenant_id="tenant_b")

        resp = _export_request(client, tenant_id="tenant_a", totp_code=_totp_code())
        assert resp.status_code == 200
        assert all(e["tenant_id"] == "tenant_a" for e in resp.json()["entries"])


def test_export_requires_totp_even_for_trusted_api_key(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_export_api_key_still_needs_totp.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        _seed_event(client, "export-api-key-guard")

    monkeypatch.setattr(security, "ALLINO_API_KEY", "trusted-master-key")

    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/admin/tenant/audit/export?tenant_id=tenant_demo",
            headers={"X-API-Key": "trusted-master-key"},
        )
        assert resp.status_code == 401

        resp = client.get(
            "/api/v1/admin/tenant/audit/export?tenant_id=tenant_demo",
            headers={"X-API-Key": "trusted-master-key", "X-TOTP-Code": _totp_code()},
        )
        assert resp.status_code == 200


def test_rotate_fails_without_totp_secret_configured(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_rotate_no_secret.db"
    monkeypatch.delenv("ALLINO_ADMIN_TOTP_SECRET", raising=False)

    with TestClient(app) as client:
        resp = _rotate_request(client, totp_code="123456")
        assert resp.status_code == 503


def test_rotate_fails_without_totp_header(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_rotate_no_header.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        resp = _rotate_request(client)
        assert resp.status_code == 401


def test_rotate_fails_with_wrong_totp_code(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_rotate_wrong_code.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        resp = _rotate_request(client, totp_code="000000")
        assert resp.status_code == 403


def test_rotate_succeeds_returns_candidate_key_and_is_audited(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_rotate_success.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)

    with TestClient(app) as client:
        resp = _rotate_request(client, totp_code=_totp_code())
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["candidate_api_key"]) >= 32
        assert "instructions" in body

        resp2 = _rotate_request(client, totp_code=_totp_code())
        assert resp2.json()["candidate_api_key"] != body["candidate_api_key"]

        audit = client.get("/api/v1/ingestion/audit?tenant_id=tenant_demo").json()
        matching = [e for e in audit if e["action"] == "admin.api_key.rotate_candidate_generated"]
        assert len(matching) == 2
        # The generated key must never be persisted in the audit trail.
        for entry in matching:
            assert body["candidate_api_key"] not in entry["metadata"]


def test_rotate_requires_totp_even_for_trusted_api_key(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "admin_rotate_api_key_still_needs_totp.db"
    monkeypatch.setenv("ALLINO_ADMIN_TOTP_SECRET", TOTP_SECRET)
    monkeypatch.setattr(security, "ALLINO_API_KEY", "trusted-master-key")

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/admin/api-key/rotate?tenant_id=tenant_demo",
            headers={"X-API-Key": "trusted-master-key"},
        )
        assert resp.status_code == 401

        resp = client.post(
            "/api/v1/admin/api-key/rotate?tenant_id=tenant_demo",
            headers={"X-API-Key": "trusted-master-key", "X-TOTP-Code": _totp_code()},
        )
        assert resp.status_code == 200
