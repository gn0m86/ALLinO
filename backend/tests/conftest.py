from app.core import rate_limit, security


def pytest_runtest_setup(item) -> None:  # pragma: no cover - test harness glue
    # Keep endpoint tests stable by default in local test mode.
    # Individual tests can override these values with monkeypatch when needed.
    security.ALLINO_ENV = "development"
    security.ALLINO_ALLOW_INSECURE_DEV = True
    security.ALLINO_API_KEY = None
    security.ALLINO_JWT_SECRET = None

    # RATE_LIMITER is a module-level singleton shared across the whole pytest
    # session (real wall-clock window, not per-test). Without clearing it here,
    # a test file that happens to make enough requests to a given
    # client_ip+tenant key can push a later, unrelated test file over the
    # threshold within the same 60s window -- order-dependent flakiness that
    # has nothing to do with the later test's own behavior. Reset before every
    # test for isolation; test_rate_limiting.py's own explicit .clear() calls
    # remain harmless/redundant on top of this.
    rate_limit.RATE_LIMITER.clear()
