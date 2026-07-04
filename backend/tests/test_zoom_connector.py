import pytest
import httpx

from app.connectors.base import RetryPolicy
from app.connectors.zoom_connector import ZoomConnector, map_zoom_event_to_unified_event


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.zoom.us/v2/users/me/meetings")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError("provider error", request=request, response=response)


def test_map_zoom_event_to_unified_event() -> None:
    payload = {
        "id": "823456",
        "uuid": "uuid-1",
        "topic": "Daily Incident Sync",
        "host_email": "ops@example.com",
        "start_time": "2026-07-01T11:30:00Z",
        "join_url": "https://zoom.us/j/823456",
    }

    event = map_zoom_event_to_unified_event(payload, tenant_id="tenant_demo")

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "zoom"
    assert event["externalId"] == "823456"
    assert "Daily Incident Sync" in event["payload"]["text"]


def test_zoom_connector_fetch_seeded_events() -> None:
    connector = ZoomConnector(
        tenant_id="tenant_demo",
        seeded_events=[
            {
                "id": "823456",
                "uuid": "uuid-1",
                "topic": "Daily Incident Sync",
                "host_email": "ops@example.com",
                "start_time": "2026-07-01T11:30:00Z",
                "join_url": "https://zoom.us/j/823456",
            }
        ],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "zoom-meeting-823456"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"


def test_zoom_connector_retries_and_succeeds(monkeypatch) -> None:
    connector = ZoomConnector(
        tenant_id="tenant_demo",
        token="zoom-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def flaky_fetch() -> list[dict[str, str]]:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient provider error")
        return [
            {
                "id": "823999",
                "uuid": "uuid-r",
                "topic": "Recovered fetch",
                "host_email": "ops@example.com",
                "start_time": "2026-07-01T11:30:00Z",
            }
        ]

    monkeypatch.setattr(connector, "_fetch_meetings_from_api", flaky_fetch)

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert attempts["count"] == 3
    assert connector.last_retry_count == 2


def test_zoom_connector_retries_and_fails(monkeypatch) -> None:
    connector = ZoomConnector(
        tenant_id="tenant_demo",
        token="zoom-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def always_fail() -> list[dict[str, str]]:
        attempts["count"] += 1
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(connector, "_fetch_meetings_from_api", always_fail)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        list(connector.fetch_events())

    assert attempts["count"] == 3
    assert connector.last_retry_count == 2


def test_zoom_connector_does_not_retry_on_401(monkeypatch) -> None:
    connector = ZoomConnector(
        tenant_id="tenant_demo",
        token="zoom-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def unauthorized() -> list[dict[str, str]]:
        attempts["count"] += 1
        raise _http_status_error(401)

    monkeypatch.setattr(connector, "_fetch_meetings_from_api", unauthorized)

    with pytest.raises(httpx.HTTPStatusError):
        list(connector.fetch_events())

    assert attempts["count"] == 1
    assert connector.last_retry_count == 0


def test_zoom_connector_retries_on_429(monkeypatch) -> None:
    connector = ZoomConnector(
        tenant_id="tenant_demo",
        token="zoom-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def rate_limited() -> list[dict[str, str]]:
        attempts["count"] += 1
        raise _http_status_error(429)

    monkeypatch.setattr(connector, "_fetch_meetings_from_api", rate_limited)

    with pytest.raises(httpx.HTTPStatusError):
        list(connector.fetch_events())

    assert attempts["count"] == 3
    assert connector.last_retry_count == 2
