from fastapi.testclient import TestClient

from app.api import ingestion
from app.db import session
from app.main import app


def test_unhandled_exception_returns_generic_body_with_error_id(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "sanitized_errors.db"

    def _boom(**kwargs):
        raise RuntimeError("db connection string: postgres://user:secret@internal-host/db")

    monkeypatch.setattr(ingestion, "list_messages_page", _boom)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/ingestion/inbox/page?tenant_id=tenant_demo&limit=2"
        )

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "Internal server error"
    assert "error_id" in body and body["error_id"]
    assert "secret" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text


def test_known_http_exception_paths_are_unaffected(tmp_path) -> None:
    session.DB_PATH = tmp_path / "sanitized_errors_http.db"

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/inbox/page?tenant_id=tenant_demo&limit=2&cursor=not-a-valid-cursor"
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid inbox cursor"
