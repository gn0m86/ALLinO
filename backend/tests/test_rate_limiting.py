from fastapi.testclient import TestClient

from app.core import rate_limit
from app.db import session
from app.main import app


def test_rate_limit_blocks_after_threshold(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "rate_limit_threshold.db"

    monkeypatch.setattr(rate_limit, "ALLINO_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit, "ALLINO_RATE_LIMIT_REQUESTS", 2)
    monkeypatch.setattr(rate_limit, "ALLINO_RATE_LIMIT_WINDOW_SECONDS", 60)
    rate_limit.RATE_LIMITER.clear()

    with TestClient(app) as client:
        r1 = client.get("/api/v1/ingestion/stats?tenant_id=tenant_demo")
        r2 = client.get("/api/v1/ingestion/stats?tenant_id=tenant_demo")
        r3 = client.get("/api/v1/ingestion/stats?tenant_id=tenant_demo")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json()["detail"] == "Rate limit exceeded"
    assert int(r3.headers["Retry-After"]) >= 1


def test_rate_limit_ignores_non_ingestion_paths(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit, "ALLINO_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit, "ALLINO_RATE_LIMIT_REQUESTS", 1)
    monkeypatch.setattr(rate_limit, "ALLINO_RATE_LIMIT_WINDOW_SECONDS", 60)
    rate_limit.RATE_LIMITER.clear()

    with TestClient(app) as client:
        r1 = client.get("/health")
        r2 = client.get("/health")

    assert r1.status_code == 200
    assert r2.status_code == 200
