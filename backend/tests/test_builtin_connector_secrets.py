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
