import json
import importlib.util
from pathlib import Path


def _load_dlq_smoke_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "staging_smoke_external_worker_dlq.py"
    spec = importlib.util.spec_from_file_location("staging_smoke_external_worker_dlq", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dlq_smoke = _load_dlq_smoke_module()


class _FakeRedisClient:
    def __init__(self) -> None:
        self.value = 0

    def xlen(self, stream):
        return self.value


class _FakeResponse:
    def __init__(self, body: dict) -> None:
        self.status_code = 200
        self._body = body
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._body


def test_dlq_smoke_success(monkeypatch, tmp_path: Path) -> None:
    fake_redis = _FakeRedisClient()

    class _FakeRedisModule:
        @staticmethod
        def from_url(url, decode_responses=True):
            return fake_redis

    monkeypatch.setattr(dlq_smoke, "redis", _FakeRedisModule)

    def fake_post(url, headers, json, timeout):
        fake_redis.value = 1
        return _FakeResponse({"event_bus": "redis_fallback", "reason": "external_worker_error_result"})

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)

    output = tmp_path / "dlq.json"
    code = dlq_smoke.run_dlq_smoke(
        backend_url="http://localhost:8000",
        tenant_id="tenant_demo",
        api_key="api",
        redis_url="redis://localhost:6379/0",
        dlq_stream="allino:ingestion:dlq",
        output_path=str(output),
    )

    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["dlq_delta"] > 0


def test_dlq_smoke_failure(monkeypatch, tmp_path: Path) -> None:
    fake_redis = _FakeRedisClient()

    class _FakeRedisModule:
        @staticmethod
        def from_url(url, decode_responses=True):
            return fake_redis

    monkeypatch.setattr(dlq_smoke, "redis", _FakeRedisModule)

    def fake_post(url, headers, json, timeout):
        return _FakeResponse({"event_bus": "external_worker", "reason": None})

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)

    output = tmp_path / "dlq_fail.json"
    code = dlq_smoke.run_dlq_smoke(
        backend_url="http://localhost:8000",
        tenant_id="tenant_demo",
        api_key="api",
        redis_url="redis://localhost:6379/0",
        dlq_stream="allino:ingestion:dlq",
        output_path=str(output),
    )

    assert code == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is False
