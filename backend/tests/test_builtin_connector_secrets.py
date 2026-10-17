from fastapi.testclient import TestClient

from app.db import session
from app.db.session import init_db
from app.db.repositories.builtin_connector_secrets_repo import (
    delete_builtin_connector_secret,
    get_builtin_connector_secret,
    list_builtin_connector_secrets,
    upsert_builtin_connector_secret,
)
from app.main import app


def test_repo_upsert_and_get_roundtrips_config(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_roundtrip.db"
    init_db()

    upsert_builtin_connector_secret(
        tenant_id="tenant_a",
        source_type="github",
        config={"token": "ghp_example"},
        poll_interval_seconds=300,
    )
    row = get_builtin_connector_secret(tenant_id="tenant_a", source_type="github")

    assert row is not None
    assert row["config"] == {"token": "ghp_example"}
    assert row["poll_interval_seconds"] == 300
    assert row["status"] == "active"


def test_repo_upsert_overwrites_existing_row_not_duplicate(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_overwrite.db"
    init_db()

    upsert_builtin_connector_secret(
        tenant_id="tenant_a", source_type="github", config={"token": "old"}, poll_interval_seconds=300
    )
    upsert_builtin_connector_secret(
        tenant_id="tenant_a", source_type="github", config={"token": "new"}, poll_interval_seconds=600
    )

    rows = list_builtin_connector_secrets(tenant_id="tenant_a")
    assert len(rows) == 1
    assert rows[0]["config"] == {"token": "new"}
    assert rows[0]["poll_interval_seconds"] == 600


def test_repo_raw_db_value_is_encrypted_at_rest(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_encrypted.db"
    init_db()

    from app.core import config as core_config
    from app.core import crypto

    monkeypatch.setattr(core_config, "ALLINO_ENCRYPTION_AT_REST_ENABLED", True)
    monkeypatch.setattr(crypto, "ALLINO_ENCRYPTION_AT_REST_ENABLED", True)
    monkeypatch.setattr(crypto, "ALLINO_ENCRYPTION_KEY", "test-encryption-key-value")
    monkeypatch.setattr(crypto, "_CACHED_FERNET", None)

    upsert_builtin_connector_secret(
        tenant_id="tenant_a",
        source_type="github",
        config={"token": "super-secret-token"},
        poll_interval_seconds=300,
    )

    with session.get_connection() as conn:
        raw = conn.execute(
            "SELECT encrypted_config FROM builtin_connector_secrets WHERE tenant_id = ? AND source_type = ?",
            ("tenant_a", "github"),
        ).fetchone()

    assert "super-secret-token" not in raw["encrypted_config"]
    assert raw["encrypted_config"].startswith("enc:v1:")

    decrypted = get_builtin_connector_secret(tenant_id="tenant_a", source_type="github")
    assert decrypted["config"]["token"] == "super-secret-token"


def test_repo_delete_removes_row(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_delete.db"
    init_db()

    upsert_builtin_connector_secret(
        tenant_id="tenant_a", source_type="slack", config={"token": "x"}, poll_interval_seconds=60
    )
    assert delete_builtin_connector_secret(tenant_id="tenant_a", source_type="slack") is True
    assert get_builtin_connector_secret(tenant_id="tenant_a", source_type="slack") is None
    assert delete_builtin_connector_secret(tenant_id="tenant_a", source_type="slack") is False


def test_api_create_list_and_delete_builtin_secret(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_crud.db"

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/v1/ingestion/connectors/builtin/github/secret?tenant_id=tenant_demo",
            json={"token": "ghp_example", "poll_interval_seconds": 300},
        )
        assert create_resp.status_code == 200
        body = create_resp.json()
        assert body["source_type"] == "github"
        assert body["configured"] is True
        assert body["poll_interval_seconds"] == 300
        assert "token" not in body

        list_resp = client.get("/api/v1/ingestion/connectors/builtin/secrets?tenant_id=tenant_demo")
        assert list_resp.status_code == 200
        sources = [row["source_type"] for row in list_resp.json()]
        assert sources == ["github"]

        delete_resp = client.delete(
            "/api/v1/ingestion/connectors/builtin/github/secret?tenant_id=tenant_demo"
        )
        assert delete_resp.status_code == 200

        list_after = client.get("/api/v1/ingestion/connectors/builtin/secrets?tenant_id=tenant_demo")
        assert list_after.json() == []


def test_api_delete_nonexistent_secret_returns_404(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_404.db"

    with TestClient(app) as client:
        resp = client.delete(
            "/api/v1/ingestion/connectors/builtin/github/secret?tenant_id=tenant_demo"
        )
        assert resp.status_code == 404


def test_api_rocketchat_requires_user_id_and_base_url(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_rocketchat_required.db"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/connectors/builtin/rocketchat/secret?tenant_id=tenant_demo",
            json={"token": "rc_token"},
        )
        assert resp.status_code == 422


def test_api_rocketchat_accepts_full_config(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_rocketchat_ok.db"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/connectors/builtin/rocketchat/secret?tenant_id=tenant_demo",
            json={
                "token": "rc_token",
                "user_id": "rc_user",
                "base_url": "https://chat.example.invalid",
                "channel_id": "general",
            },
        )
        assert resp.status_code == 200


def test_api_invalid_source_type_returns_422(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_bad_source.db"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/connectors/builtin/not-a-real-source/secret?tenant_id=tenant_demo",
            json={"token": "x"},
        )
        assert resp.status_code == 422


def test_api_secrets_are_tenant_isolated(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_tenant_isolation.db"

    with TestClient(app) as client:
        client.post(
            "/api/v1/ingestion/connectors/builtin/github/secret?tenant_id=tenant_a",
            json={"token": "a-token"},
        )

        list_b = client.get("/api/v1/ingestion/connectors/builtin/secrets?tenant_id=tenant_b")
        assert list_b.json() == []


def test_sync_builtin_connector_secret_raises_when_not_configured(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_sync_not_configured.db"
    init_db()

    from app.services.connector_sync import (
        BuiltinConnectorSecretNotConfiguredError,
        sync_builtin_connector_secret,
    )
    import pytest

    with pytest.raises(BuiltinConnectorSecretNotConfiguredError):
        sync_builtin_connector_secret(tenant_id="tenant_demo", source_type="github")


def test_sync_builtin_connector_secret_constructs_connector_from_config(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_sync_constructs.db"
    init_db()

    from app.connectors.rocketchat_connector import RocketChatConnector
    from app.services import connector_sync

    upsert_builtin_connector_secret(
        tenant_id="tenant_demo",
        source_type="rocketchat",
        config={
            "token": "rc-token",
            "user_id": "rc-user",
            "base_url": "https://chat.example.invalid",
            "channel_id": "GENERAL",
        },
        poll_interval_seconds=None,
    )

    seen: dict = {}

    def fake_sync(*, connector, source, tenant_id, action_prefix):
        seen["connector"] = connector
        seen["source"] = source
        seen["tenant_id"] = tenant_id
        return {"tenant_id": tenant_id, "processed": 1, "inserted": 1, "duplicates": 0, "rejected": 0}

    monkeypatch.setattr(connector_sync, "sync_builtin_connector", fake_sync)

    result = connector_sync.sync_builtin_connector_secret(tenant_id="tenant_demo", source_type="rocketchat")

    assert result["processed"] == 1
    assert seen["source"] == "rocketchat"
    assert seen["tenant_id"] == "tenant_demo"
    assert isinstance(seen["connector"], RocketChatConnector)
    assert seen["connector"].token == "rc-token"
    assert seen["connector"].user_id == "rc-user"
    assert seen["connector"].base_url == "https://chat.example.invalid"
    assert seen["connector"].channel_id == "GENERAL"


def test_sync_builtin_connector_secret_routes_google_calendar(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_sync_gcal.db"
    init_db()

    from app.services import connector_sync

    upsert_builtin_connector_secret(
        tenant_id="tenant_demo",
        source_type="google_calendar",
        config={"token": "gcal-token", "calendar_id": "team@example.invalid"},
        poll_interval_seconds=None,
    )

    seen: dict = {}

    def fake_sync(*, tenant_id, calendar_id=None, token=None, client_id=None, client_secret=None, refresh_token=None, retry_policy=None, seeded_events=None):
        seen["tenant_id"] = tenant_id
        seen["calendar_id"] = calendar_id
        seen["token"] = token
        return {"tenant_id": tenant_id, "processed": 0, "inserted": 0, "duplicates": 0, "rejected": 0}

    monkeypatch.setattr(connector_sync, "sync_google_calendar_connector", fake_sync)

    connector_sync.sync_builtin_connector_secret(tenant_id="tenant_demo", source_type="google_calendar")

    assert seen == {"tenant_id": "tenant_demo", "calendar_id": "team@example.invalid", "token": "gcal-token"}


def test_api_sync_endpoint_404_when_not_configured(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_sync_404.db"

    with TestClient(app) as client:
        resp = client.post("/api/v1/ingestion/connectors/builtin/github/sync?tenant_id=tenant_demo")
        assert resp.status_code == 404


def test_api_sync_endpoint_success(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_sync_success.db"

    from app.api import builtin_connector_secrets as api_module

    def fake_sync(*, tenant_id, source_type):
        return {"tenant_id": tenant_id, "processed": 3, "inserted": 2, "duplicates": 1, "rejected": 0}

    monkeypatch.setattr(api_module, "sync_builtin_connector_secret", fake_sync)

    with TestClient(app) as client:
        client.post(
            "/api/v1/ingestion/connectors/builtin/github/secret?tenant_id=tenant_demo",
            json={"token": "ghp_example"},
        )

        resp = client.post("/api/v1/ingestion/connectors/builtin/github/sync?tenant_id=tenant_demo")

        assert resp.status_code == 200
        assert resp.json()["inserted"] == 2


def test_api_sync_endpoint_502_on_sync_error(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_sync_error.db"

    import httpx

    from app.connectors.github_connector import GitHubConnector

    def unauthorized(self: GitHubConnector) -> list[dict]:
        request = httpx.Request("GET", "https://api.github.com/notifications")
        response = httpx.Response(status_code=401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(GitHubConnector, "_fetch_notifications_from_api", unauthorized)

    with TestClient(app) as client:
        client.post(
            "/api/v1/ingestion/connectors/builtin/github/secret?tenant_id=tenant_demo",
            json={"token": "invalid-token"},
        )

        resp = client.post("/api/v1/ingestion/connectors/builtin/github/sync?tenant_id=tenant_demo")
        assert resp.status_code == 502


def test_api_google_calendar_accepts_oauth_refresh_trio_without_token(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_gcal_oauth.db"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/connectors/builtin/google_calendar/secret?tenant_id=tenant_demo",
            json={
                "client_id": "client-123",
                "client_secret": "secret-abc",
                "refresh_token": "refresh-xyz",
                "calendar_id": "team@example.invalid",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["configured"] is True


def test_api_google_calendar_rejects_without_token_or_full_oauth_trio(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_gcal_incomplete.db"

    with TestClient(app) as client:
        # No token, and only a partial OAuth trio (missing refresh_token).
        resp = client.post(
            "/api/v1/ingestion/connectors/builtin/google_calendar/secret?tenant_id=tenant_demo",
            json={"client_id": "client-123", "client_secret": "secret-abc"},
        )
        assert resp.status_code == 422


def test_api_google_calendar_still_accepts_plain_token(tmp_path) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_gcal_plain_token.db"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/connectors/builtin/google_calendar/secret?tenant_id=tenant_demo",
            json={"token": "raw-access-token"},
        )
        assert resp.status_code == 200


def test_api_google_calendar_sync_uses_oauth_refresh_flow(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "builtin_secrets_api_gcal_oauth_sync.db"

    from app.connectors.google_calendar_connector import GoogleCalendarConnector

    monkeypatch.setattr(
        "app.connectors.google_calendar_connector.refresh_google_access_token",
        lambda *, client_id, client_secret, refresh_token: "minted-token",
    )

    seen_tokens = []

    def fake_fetch(self) -> list[dict]:
        seen_tokens.append(self.token)
        return []

    monkeypatch.setattr(GoogleCalendarConnector, "_fetch_events_from_api", fake_fetch)

    with TestClient(app) as client:
        client.post(
            "/api/v1/ingestion/connectors/builtin/google_calendar/secret?tenant_id=tenant_demo",
            json={"client_id": "client-123", "client_secret": "secret-abc", "refresh_token": "refresh-xyz"},
        )

        resp = client.post(
            "/api/v1/ingestion/connectors/builtin/google_calendar/sync?tenant_id=tenant_demo"
        )

        assert resp.status_code == 200
        assert seen_tokens == ["minted-token"]
