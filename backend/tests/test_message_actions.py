import jwt
from fastapi.testclient import TestClient

from app.core import security
from app.db import session
from app.db.repositories.messages_repo import snooze_message
from app.main import app


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


def _archived_ids(client: TestClient, tenant_id: str = "tenant_demo") -> set[str]:
    resp = client.get(f"/api/v1/ingestion/inbox?tenant_id={tenant_id}&archived=true")
    assert resp.status_code == 200
    return {item["event_id"] for item in resp.json()}


def test_archive_unknown_message_returns_404(tmp_path) -> None:
    session.DB_PATH = tmp_path / "archive_unknown.db"

    with TestClient(app) as client:
        resp = client.post("/api/v1/ingestion/messages/does-not-exist/archive?tenant_id=tenant_demo")
        assert resp.status_code == 404


def test_snooze_unknown_message_returns_404(tmp_path) -> None:
    session.DB_PATH = tmp_path / "snooze_unknown.db"

    with TestClient(app) as client:
        resp = client.post("/api/v1/ingestion/messages/does-not-exist/snooze?tenant_id=tenant_demo")
        assert resp.status_code == 404


def test_archive_hides_message_from_inbox_and_is_audited(tmp_path) -> None:
    session.DB_PATH = tmp_path / "archive_hides.db"

    with TestClient(app) as client:
        _seed_event(client, "a1")
        assert "a1" in _inbox_ids(client)

        resp = client.post("/api/v1/ingestion/messages/a1/archive?tenant_id=tenant_demo")
        assert resp.status_code == 200
        assert resp.json() == {"status": "archived", "event_id": "a1"}

        assert "a1" not in _inbox_ids(client)

        audit = client.get("/api/v1/ingestion/audit?tenant_id=tenant_demo").json()
        actions = [entry["action"] for entry in audit]
        assert "message.archived" in actions


def test_archived_message_appears_in_archived_view(tmp_path) -> None:
    session.DB_PATH = tmp_path / "archived_view.db"

    with TestClient(app) as client:
        _seed_event(client, "a2")
        assert "a2" not in _archived_ids(client)

        resp = client.post("/api/v1/ingestion/messages/a2/archive?tenant_id=tenant_demo")
        assert resp.status_code == 200

        # Archived: gone from the normal inbox, but visible in the archived view.
        assert "a2" not in _inbox_ids(client)
        assert "a2" in _archived_ids(client)


def test_unarchive_unknown_message_returns_404(tmp_path) -> None:
    session.DB_PATH = tmp_path / "unarchive_unknown.db"

    with TestClient(app) as client:
        resp = client.post("/api/v1/ingestion/messages/does-not-exist/unarchive?tenant_id=tenant_demo")
        assert resp.status_code == 404


def test_unarchive_restores_message_to_inbox_and_is_audited(tmp_path) -> None:
    session.DB_PATH = tmp_path / "unarchive_restores.db"

    with TestClient(app) as client:
        _seed_event(client, "a3")
        client.post("/api/v1/ingestion/messages/a3/archive?tenant_id=tenant_demo")
        assert "a3" not in _inbox_ids(client)
        assert "a3" in _archived_ids(client)

        resp = client.post("/api/v1/ingestion/messages/a3/unarchive?tenant_id=tenant_demo")
        assert resp.status_code == 200
        assert resp.json() == {"status": "active", "event_id": "a3"}

        assert "a3" in _inbox_ids(client)
        assert "a3" not in _archived_ids(client)

        audit = client.get("/api/v1/ingestion/audit?tenant_id=tenant_demo").json()
        actions = [entry["action"] for entry in audit]
        assert "message.unarchived" in actions


def test_snooze_hides_message_from_inbox_with_default_duration(tmp_path) -> None:
    session.DB_PATH = tmp_path / "snooze_hides.db"

    with TestClient(app) as client:
        _seed_event(client, "s1")
        assert "s1" in _inbox_ids(client)

        resp = client.post("/api/v1/ingestion/messages/s1/snooze?tenant_id=tenant_demo")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "snoozed"
        assert body["event_id"] == "s1"
        assert "snoozed_until" in body

        assert "s1" not in _inbox_ids(client)

        audit = client.get("/api/v1/ingestion/audit?tenant_id=tenant_demo").json()
        actions = [entry["action"] for entry in audit]
        assert "message.snoozed" in actions


def test_snooze_accepts_custom_duration(tmp_path) -> None:
    session.DB_PATH = tmp_path / "snooze_custom.db"

    with TestClient(app) as client:
        _seed_event(client, "s2")

        resp = client.post(
            "/api/v1/ingestion/messages/s2/snooze?tenant_id=tenant_demo",
            json={"hours": 1},
        )
        assert resp.status_code == 200
        assert "s2" not in _inbox_ids(client)


def test_snooze_rejects_out_of_range_duration(tmp_path) -> None:
    session.DB_PATH = tmp_path / "snooze_invalid.db"

    with TestClient(app) as client:
        _seed_event(client, "s3")

        resp = client.post(
            "/api/v1/ingestion/messages/s3/snooze?tenant_id=tenant_demo",
            json={"hours": 0},
        )
        assert resp.status_code == 422


def test_snoozed_message_reappears_once_expired(tmp_path) -> None:
    session.DB_PATH = tmp_path / "snooze_expired.db"

    with TestClient(app) as client:
        _seed_event(client, "s4")
        assert "s4" in _inbox_ids(client)

        # Directly exercise the repo layer with a past timestamp to verify the
        # inbox listing's active-filter treats an elapsed snooze as visible
        # again, without needing to manipulate wall-clock time in the test.
        snooze_message(tenant_id="tenant_demo", event_id="s4", snoozed_until="2000-01-01T00:00:00+00:00")

        assert "s4" in _inbox_ids(client)


def test_archive_and_snooze_are_tenant_scoped(tmp_path) -> None:
    session.DB_PATH = tmp_path / "message_actions_tenant.db"

    with TestClient(app) as client:
        _seed_event(client, "t1", tenant_id="tenant_a")

        resp = client.post("/api/v1/ingestion/messages/t1/archive?tenant_id=tenant_b")
        assert resp.status_code == 404

        resp = client.post("/api/v1/ingestion/messages/t1/snooze?tenant_id=tenant_b")
        assert resp.status_code == 404

        resp = client.post("/api/v1/ingestion/messages/t1/unarchive?tenant_id=tenant_b")
        assert resp.status_code == 404

        assert "t1" in _inbox_ids(client, tenant_id="tenant_a")


def test_message_actions_forbidden_without_required_jwt_claims(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "message_actions_perm_forbidden.db"

    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_MESSAGE_ACTIONS_ROLES", {"admin"})
    monkeypatch.setattr(security, "ALLINO_JWT_MESSAGE_ACTIONS_SCOPES", {"messages:archive"})

    token = jwt.encode(
        {"sub": "user-no-perm", "scope": "read:only", "tenant_id": "tenant_demo"},
        "jwt-secret",
        algorithm="HS256",
    )

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/messages/does-not-exist/archive?tenant_id=tenant_demo",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


def test_message_actions_allowed_with_jwt_scope(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "message_actions_perm_allowed.db"

    # Seed under the default insecure-dev conftest state, before locking the
    # security module down to JWT-only auth below -- otherwise this seed call
    # would itself need a bearer token.
    with TestClient(app) as client:
        _seed_event(client, "j1")

    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_MESSAGE_ACTIONS_ROLES", {"admin"})
    monkeypatch.setattr(security, "ALLINO_JWT_MESSAGE_ACTIONS_SCOPES", {"messages:archive"})

    token = jwt.encode(
        {"sub": "message-actions-user", "scope": "read messages:archive", "tenant_id": "tenant_demo"},
        "jwt-secret",
        algorithm="HS256",
    )

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/messages/j1/archive?tenant_id=tenant_demo",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
