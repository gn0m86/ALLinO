from app.services import event_bus


def _processor(events, tenant_id, action_prefix):
    return {
        "processed": len(events),
        "inserted": len(events),
        "duplicates": 0,
        "rejected": 0,
        "total_lag_ms": 0.0,
        "lag_samples": 0,
    }


def test_event_bus_direct_mode_when_feature_disabled(monkeypatch) -> None:
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ENABLED", False)

    events = [{"eventId": "e1"}, {"eventId": "e2"}]
    counts, meta = event_bus.process_connector_events(
        tenant_id="tenant_demo",
        source="github",
        action_prefix="connector.github.sync",
        events=events,
        processor=_processor,
    )

    assert counts["processed"] == 2
    assert meta["mode"] == event_bus.EventBusMode.DIRECT
    assert meta["published"] == 2
    assert meta["consumed"] == 2


def test_event_bus_falls_back_when_redis_missing(monkeypatch) -> None:
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED", False)
    monkeypatch.setattr(event_bus, "redis", None)

    events = [{"eventId": "e1"}]
    counts, meta = event_bus.process_connector_events(
        tenant_id="tenant_demo",
        source="github",
        action_prefix="connector.github.sync",
        events=events,
        processor=_processor,
    )

    assert counts["processed"] == 1
    assert meta["mode"] == event_bus.EventBusMode.REDIS_FALLBACK
    assert meta["reason"] == "redis_not_installed"


def test_event_bus_async_worker_mode(monkeypatch) -> None:
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_TIMEOUT_SECONDS", 1.0)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS", 3)

    events = [{"eventId": "e1"}, {"eventId": "e2"}, {"eventId": "e3"}]
    counts, meta = event_bus.process_connector_events(
        tenant_id="tenant_demo",
        source="github",
        action_prefix="connector.github.sync",
        events=events,
        processor=_processor,
    )

    assert counts["processed"] == 3
    assert meta["mode"] == event_bus.EventBusMode.WORKER_ASYNC
    assert meta["published"] == 3
    assert meta["consumed"] == 3
    assert meta["worker_attempts"] == 1


def test_event_bus_async_worker_retries_and_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_TIMEOUT_SECONDS", 1.0)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS", 3)

    attempts = {"count": 0}

    def flaky_processor(events, tenant_id, action_prefix):
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("transient worker failure")
        return {
            "processed": len(events),
            "inserted": len(events),
            "duplicates": 0,
            "rejected": 0,
            "total_lag_ms": 0.0,
            "lag_samples": 0,
        }

    events = [{"eventId": "e1"}]
    counts, meta = event_bus.process_connector_events(
        tenant_id="tenant_demo",
        source="github",
        action_prefix="connector.github.sync",
        events=events,
        processor=flaky_processor,
    )

    assert attempts["count"] == 2
    assert counts["processed"] == 1
    assert meta["mode"] == event_bus.EventBusMode.WORKER_ASYNC
    assert meta["worker_attempts"] == 2


def test_event_bus_async_worker_fallback_on_exhausted_retries(monkeypatch) -> None:
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED", True)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_TIMEOUT_SECONDS", 1.0)
    monkeypatch.setattr(event_bus, "ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS", 2)

    attempts = {"count": 0}

    def always_fail_processor(events, tenant_id, action_prefix):
        attempts["count"] += 1
        raise RuntimeError("worker failure")

    def direct_fallback_processor(events, tenant_id, action_prefix):
        return {
            "processed": len(events),
            "inserted": len(events),
            "duplicates": 0,
            "rejected": 0,
            "total_lag_ms": 0.0,
            "lag_samples": 0,
        }

    def combined_processor(events, tenant_id, action_prefix):
        if attempts["count"] < 2:
            return always_fail_processor(events, tenant_id, action_prefix)
        return direct_fallback_processor(events, tenant_id, action_prefix)

    events = [{"eventId": "e1"}, {"eventId": "e2"}]
    counts, meta = event_bus.process_connector_events(
        tenant_id="tenant_demo",
        source="github",
        action_prefix="connector.github.sync",
        events=events,
        processor=combined_processor,
    )

    assert counts["processed"] == 2
    assert meta["mode"] == event_bus.EventBusMode.REDIS_FALLBACK
    assert meta["reason"] == "worker_error"
    assert meta["worker_attempts"] == 2
