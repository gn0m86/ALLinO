from fastapi.testclient import TestClient

from app.main import _docs_enabled_for_env, app


def test_docs_disabled_in_production() -> None:
    assert _docs_enabled_for_env("production") is False


def test_docs_enabled_outside_production() -> None:
    assert _docs_enabled_for_env("development") is True
    assert _docs_enabled_for_env("staging") is True


def test_docs_reachable_in_current_test_env() -> None:
    # The running `app` was already constructed at import time under
    # ALLINO_ENV=development (this test suite's default) -- confirms the
    # FastAPI wiring actually uses the flag, not just the helper in isolation.
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200
