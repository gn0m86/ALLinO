import jwt
from fastapi.testclient import TestClient

from app.core import security
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


def test_sync_endpoint_forbidden_without_required_jwt_claims(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "sync_perm_forbidden.db"

    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_ROLES", {"admin", "operator"})
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_SCOPES", {"connectors:sync"})

    token = jwt.encode(
        {"sub": "user-no-sync", "scope": "read:only", "tenant_id": "tenant_demo"},
        "jwt-secret",
        algorithm="HS256",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={"seeded_notifications": [_notification("gh-no-perm")]},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


def test_sync_endpoint_allows_jwt_scope_for_connector_sync(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "sync_perm_allowed.db"

    monkeypatch.setattr(security, "ALLINO_API_KEY", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SECRET", "jwt-secret")
    monkeypatch.setattr(security, "ALLINO_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "ALLINO_JWT_ISSUER", None)
    monkeypatch.setattr(security, "ALLINO_JWT_AUDIENCE", None)
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_ROLES", {"admin", "operator"})
    monkeypatch.setattr(security, "ALLINO_JWT_SYNC_SCOPES", {"connectors:sync"})

    token = jwt.encode(
        {"sub": "sync-user", "scope": "read connectors:sync", "tenant_id": "tenant_demo"},
        "jwt-secret",
        algorithm="HS256",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo",
            json={"seeded_notifications": [_notification("gh-with-scope")]},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["processed"] == 1
    assert data["inserted"] == 1
