import jwt
from fastapi.testclient import TestClient

from app.core import security
from app.db import session
from app.main import app


def test_read_endpoint_forbidden_without_required_jwt_claims(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "read_perm_forbidden.db"

    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_READ_ROLES", {"viewer", "analyst"})
    monkeypatch.setattr(security, "ALLINO_JWT_READ_SCOPES", {"inbox:read", "metrics:read"})

    token = jwt.encode(
        {"sub": "read-no-access", "scope": "read:other", "tenant_id": "tenant_demo"},
        "jwt-secret",
        algorithm="HS256",
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/inbox?tenant_id=tenant_demo",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


def test_read_endpoint_allows_jwt_scope(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "read_perm_allowed.db"

    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_READ_ROLES", {"viewer", "analyst"})
    monkeypatch.setattr(security, "ALLINO_JWT_READ_SCOPES", {"inbox:read", "metrics:read"})

    token = jwt.encode(
        {"sub": "read-user", "scope": "foo inbox:read", "tenant_id": "tenant_demo"},
        "jwt-secret",
        algorithm="HS256",
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/inbox?tenant_id=tenant_demo",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
