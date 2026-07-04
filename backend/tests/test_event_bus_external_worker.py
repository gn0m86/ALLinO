from app.services import event_bus


class _FakeRedisClient:
    def __init__(self) -> None:
        self.xadd_calls: list[tuple[str, dict[str, str]]] = []

    def xadd(self, stream: str, fields: dict[str, str]) -> str:
        self.xadd_calls.append((stream, fields))
        return "1-0"

    def get(self, key: str):
        return None


class _FakeRedisModule:
    def __init__(self, client: _FakeRedisClient) -> None:
        self._client = client

    def from_url(self, *args, **kwargs):
        return self._client


def _processor(events, tenant_id, action_prefix):
    return {
        "processed": len(events),
        "inserted": len(events),
        "duplicates": 0,
        "rejected": 0,
        "total_lag_ms": 0.0,
        "lag_samples": 0,
    }


def test_event_bus_external_worker_mode_success(monkeypatch) -> None:
    client = _FakeRedisClient()
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED", False)
    monkeypatch.setattr(event_bus, "redis", _FakeRedisModule(client))

    def fake_wait(_client, result_key: str, timeout_seconds: float):
        return {
            "processed": 2,
            "inserted": 2,
            "duplicates": 0,
            "rejected": 0,
            "total_lag_ms": 0.0,
            "lag_samples": 0,
        }

    monkeypatch.setattr(event_bus, "_wait_for_external_worker_result", fake_wait)

    counts, meta = event_bus.process_connector_events(
        tenant_id="tenant_demo",
        source="github",
        action_prefix="connector.github.sync",
        events=[{"eventId": "e1"}, {"eventId": "e2"}],
        processor=_processor,
    )

    assert counts["processed"] == 2
    assert meta["mode"] == event_bus.EventBusMode.EXTERNAL_WORKER
    assert meta["published"] == 2
    assert meta["consumed"] == 2
    assert len(client.xadd_calls) == 2


def test_event_bus_external_worker_timeout_fallback(monkeypatch) -> None:
    client = _FakeRedisClient()
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED", False)
    monkeypatch.setattr(event_bus, "redis", _FakeRedisModule(client))

    def fake_wait(_client, result_key: str, timeout_seconds: float):
        return None

    monkeypatch.setattr(event_bus, "_wait_for_external_worker_result", fake_wait)

    counts, meta = event_bus.process_connector_events(
        tenant_id="tenant_demo",
        source="github",
        action_prefix="connector.github.sync",
        events=[{"eventId": "e1"}],
        processor=_processor,
    )

    assert counts["processed"] == 1
    assert meta["mode"] == event_bus.EventBusMode.REDIS_FALLBACK
    assert meta["reason"] == "external_worker_timeout"


def test_event_bus_external_worker_error_result_fallback(monkeypatch) -> None:
    client = _FakeRedisClient()
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED", False)
    monkeypatch.setattr(event_bus, "redis", _FakeRedisModule(client))

    def fake_wait(_client, result_key: str, timeout_seconds: float):
        return {
            "processed": 0,
            "inserted": 0,
            "duplicates": 0,
            "rejected": 1,
            "total_lag_ms": 0.0,
            "lag_samples": 0,
            "attempts": 3,
            "error": "worker failed",
        }

    monkeypatch.setattr(event_bus, "_wait_for_external_worker_result", fake_wait)

    counts, meta = event_bus.process_connector_events(
        tenant_id="tenant_demo",
        source="github",
        action_prefix="connector.github.sync",
        events=[{"eventId": "e1"}],
        processor=_processor,
    )

    assert counts["processed"] == 1
    assert meta["mode"] == event_bus.EventBusMode.REDIS_FALLBACK
    assert meta["reason"] == "external_worker_error_result"
    assert meta["worker_attempts"] == 3
