from fastapi.testclient import TestClient

from app.core import security_headers
from app.main import app


def test_security_headers_present_on_response(monkeypatch) -> None:
    monkeypatch.setattr(security_headers, "ALLINO_SECURITY_HEADERS_ENABLED", True)
    monkeypatch.setattr(security_headers, "ALLINO_CSP_POLICY", "default-src 'self'")
    monkeypatch.setattr(security_headers, "ALLINO_HSTS_ENABLED", False)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["Content-Security-Policy"] == "default-src 'self'"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_added_for_https_requests(monkeypatch) -> None:
    monkeypatch.setattr(security_headers, "ALLINO_SECURITY_HEADERS_ENABLED", True)
    monkeypatch.setattr(security_headers, "ALLINO_HSTS_ENABLED", True)
    monkeypatch.setattr(security_headers, "ALLINO_HSTS_MAX_AGE", 31536000)
    monkeypatch.setattr(security_headers, "ALLINO_HSTS_INCLUDE_SUBDOMAINS", True)
    monkeypatch.setattr(security_headers, "ALLINO_HSTS_PRELOAD", False)

    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Forwarded-Proto": "https"})

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_security_headers_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setattr(security_headers, "ALLINO_SECURITY_HEADERS_ENABLED", False)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    assert "X-Frame-Options" not in response.headers
    assert "X-Content-Type-Options" not in response.headers
