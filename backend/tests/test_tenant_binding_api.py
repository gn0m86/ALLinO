import jwt
from fastapi.testclient import TestClient

from app.core import security
from app.db import session
from app.main import app


def _token(payload: dict) -> str:
    return jwt.encode(payload, "jwt-secret", algorithm="HS256")


def _configure_jwt(monkeypatch) -> None:
    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_READ_ROLES", {"viewer", "analyst"})
    monkeypatch.setattr(security, "ALLINO_JWT_READ_SCOPES", {"inbox:read"})
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_ROLES", {"admin", "operator"})
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_SCOPES", {"connectors:sync"})


def test_jwt_tenant_claim_required_for_read_endpoint(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "tenant_claim_required.db"
    _configure_jwt(monkeypatch)

    token = _token({"sub": "u1", "scope": "inbox:read"})

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/inbox?tenant_id=tenant_demo",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert "tenant claim" in response.json()["detail"]


def test_jwt_tenant_mismatch_rejected_for_read_endpoint(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "tenant_mismatch_read.db"
    _configure_jwt(monkeypatch)

    token = _token({"sub": "u1", "scope": "inbox:read", "tenant_id": "tenant_a"})

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/inbox?tenant_id=tenant_b",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert "does not match" in response.json()["detail"]


def test_jwt_tenant_claim_is_used_when_query_omitted(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "tenant_claim_used.db"
    _configure_jwt(monkeypatch)

    token = _token({"sub": "u1", "scope": "inbox:read", "tenant_id": "tenant_demo"})

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/inbox",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_key_path_still_uses_request_tenant(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "tenant_api_key.db"

    monkeypatch.setattr(security, "ALLINO_API_KEY", "api-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/inbox?tenant_id=tenant_demo",
            headers={"X-API-Key": "api-secret"},
        )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_missing_tenant_id_without_credentials_returns_401_not_400(tmp_path, monkeypatch) -> None:
    # Regression test: resolve_tenant_id used to validate tenant_id's presence
    # before any credential was checked, so an anonymous caller who simply
    # omitted tenant_id got a 400 spelling out the exact expected request
    # shape instead of a 401 -- auth must be checked first.
    session.DB_PATH = tmp_path / "tenant_missing_no_auth.db"
    monkeypatch.setattr(security, "ALLINO_API_KEY", "api-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)

    with TestClient(app) as client:
        response = client.get("/api/v1/ingestion/inbox")

    assert response.status_code == 401


def test_missing_tenant_id_with_valid_credentials_returns_400(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "tenant_missing_with_auth.db"
    monkeypatch.setattr(security, "ALLINO_API_KEY", "api-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", None)

    with TestClient(app) as client:
        response = client.get("/api/v1/ingestion/inbox", headers={"X-API-Key": "api-secret"})

    assert response.status_code == 400
    assert "tenant_id is required" in response.json()["detail"]
