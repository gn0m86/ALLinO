import importlib.util
import json
from pathlib import Path


def _load_preflight_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "preflight_external_worker_dlq.py"
    spec = importlib.util.spec_from_file_location("preflight_external_worker_dlq", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preflight = _load_preflight_module()


class _FakeRedisClient:
    def __init__(self, ping_result=True, error: Exception | None = None):
        self._ping_result = ping_result
        self._error = error

    def ping(self):
        if self._error is not None:
            raise self._error
        return self._ping_result


def test_preflight_success(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ALLINO_EVENT_BUS_ENABLED", "true")
    monkeypatch.setenv("ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED", "true")
    monkeypatch.setenv("ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX", "connector.zoom.sync")

    class _RedisModule:
        @staticmethod
        def from_url(url, decode_responses=True):
            return _FakeRedisClient(ping_result=True)

    monkeypatch.setattr(preflight, "redis", _RedisModule)

    output = tmp_path / "preflight_ok.json"
    code = preflight.run_preflight(redis_url="redis://localhost:6379/0", output_path=str(output))

    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["checks"]["env"]["ok"] is True
    assert payload["checks"]["redis"]["ok"] is True


def test_preflight_fails_for_env_and_redis(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ALLINO_EVENT_BUS_ENABLED", raising=False)
    monkeypatch.setenv("ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED", "false")
    monkeypatch.setenv("ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX", "zoom.sync")

    class _RedisModule:
        @staticmethod
        def from_url(url, decode_responses=True):
            return _FakeRedisClient(error=RuntimeError("connection refused"))

    monkeypatch.setattr(preflight, "redis", _RedisModule)

    output = tmp_path / "preflight_fail.json"
    code = preflight.run_preflight(redis_url="redis://localhost:6379/0", output_path=str(output))

    assert code == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["checks"]["env"]["ok"] is False
    assert payload["checks"]["redis"]["ok"] is False
    assert any("Missing/invalid env requirements" in item for item in payload["errors"])
    assert any("Redis is not reachable" in item for item in payload["errors"])
