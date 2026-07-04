from fastapi.testclient import TestClient

from app.db import session
from app.main import app


def test_cors_preflight_allows_patch_for_generic_connector_update(tmp_path) -> None:
    session.DB_PATH = tmp_path / "cors_patch_preflight.db"

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/ingestion/connectors/generic/some-id",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "content-type,x-tenant-id",
            },
        )
        assert response.status_code == 200
        allowed = response.headers.get("access-control-allow-methods", "")
        assert "PATCH" in allowed


def test_cors_preflight_allows_totp_header_for_admin_delete(tmp_path) -> None:
    # Same failure mode as the PATCH lesson above, but for a custom request
    # header instead of a method: allow_headers is an explicit whitelist, so
    # adding a new header-authenticated endpoint (X-TOTP-Code) without adding
    # it here fails silently from pytest's perspective (TestClient doesn't run
    # real browser preflight) -- only visible as a real browser CORS error.
    session.DB_PATH = tmp_path / "cors_totp_preflight.db"

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/admin/tenant/messages/delete",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-tenant-id,x-totp-code",
            },
        )
        assert response.status_code == 200
        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "x-totp-code" in allowed_headers
