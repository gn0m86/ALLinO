from app.workers import event_bus_worker


class _FakeRedisClient:
    def __init__(self) -> None:
        self.setex_calls = []
        self.xadd_calls = []

    def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))

    def xadd(self, stream, fields):
        self.xadd_calls.append((stream, fields))
        return "1-0"


def _batch() -> dict:
    return {
        "tenant_id": "tenant_demo",
        "source": "github",
        "action_prefix": "connector.github.sync",
        "batch_size": 1,
        "events": {0: {"eventId": "e1"}},
    }


def test_process_completed_batch_success(monkeypatch) -> None:
    client = _FakeRedisClient()

    def ok_processor(*, events, tenant_id, action_prefix):
        return {
            "processed": len(events),
            "inserted": len(events),
            "duplicates": 0,
            "rejected": 0,
            "total_lag_ms": 0.0,
            "lag_samples": 0,
        }

    monkeypatch.setattr(event_bus_worker, "process_connector_batch", ok_processor)
    monkeypatch.setattr(event_bus_worker, "ALLINO_EVENT_BUS_EXTERNAL_WORKER_MAX_ATTEMPTS", 3)

    event_bus_worker.process_completed_batch(client=client, batch_id="b1", batch=_batch())

    assert len(client.setex_calls) == 1
    _, _, payload = client.setex_calls[0]
    assert '"processed": 1' in payload
    assert '"error": null' in payload


def test_process_completed_batch_writes_dlq_on_exhausted_retries(monkeypatch) -> None:
    client = _FakeRedisClient()

    def fail_processor(*, events, tenant_id, action_prefix):
        raise RuntimeError("boom")

    monkeypatch.setattr(event_bus_worker, "process_connector_batch", fail_processor)
    monkeypatch.setattr(event_bus_worker, "ALLINO_EVENT_BUS_EXTERNAL_WORKER_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(event_bus_worker, "ALLINO_EVENT_BUS_EXTERNAL_WORKER_BACKOFF_SECONDS", 0.0)

    event_bus_worker.process_completed_batch(client=client, batch_id="b2", batch=_batch())

    assert len(client.xadd_calls) == 1
    assert len(client.setex_calls) == 1
    _, _, payload = client.setex_calls[0]
    assert '"error": "boom"' in payload
    assert '"attempts": 2' in payload


def test_check_worker_health_without_redis(monkeypatch) -> None:
    monkeypatch.setattr(event_bus_worker, "redis", None)
    ok, message = event_bus_worker.check_worker_health()
    assert ok is False
    assert "redis package" in message
