import pytest
import httpx

from app.connectors.base import RetryPolicy
from app.connectors.google_calendar_connector import (
    GoogleCalendarConnector,
    map_google_calendar_event_to_unified_event,
)


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request(
        "GET", "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    )
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError("provider error", request=request, response=response)


def test_map_google_calendar_event_to_unified_event() -> None:
    payload = {
        "id": "evt-123",
        "summary": "Daily Incident Sync",
        "organizer": {"email": "ops@example.com"},
        "status": "confirmed",
        "start": {"dateTime": "2026-07-01T11:30:00Z"},
        "htmlLink": "https://calendar.google.com/event?eid=evt-123",
        "hangoutLink": "https://meet.google.com/abc-defg-hij",
    }

    event = map_google_calendar_event_to_unified_event(payload, tenant_id="tenant_demo")

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "google_calendar"
    assert event["externalId"] == "evt-123"
    assert "Daily Incident Sync" in event["payload"]["text"]
    assert event["payload"]["meet_url"] == "https://meet.google.com/abc-defg-hij"


def test_map_google_calendar_event_prefers_conference_data_video_entry() -> None:
    payload = {
        "id": "evt-124",
        "summary": "Postmortem Review",
        "start": {"dateTime": "2026-07-01T12:30:00Z"},
        "conferenceData": {
            "entryPoints": [
                {"entryPointType": "phone", "uri": "tel:+1234567890"},
                {"entryPointType": "video", "uri": "https://meet.google.com/xyz-uvwx-yz"},
            ]
        },
    }

    event = map_google_calendar_event_to_unified_event(payload, tenant_id="tenant_demo")

    assert event["payload"]["meet_url"] == "https://meet.google.com/xyz-uvwx-yz"


def test_map_google_calendar_event_marks_cancelled_status_in_preview() -> None:
    payload = {
        "id": "evt-125",
        "summary": "Sprint Review",
        "status": "cancelled",
        "start": {"date": "2026-07-02"},
    }

    event = map_google_calendar_event_to_unified_event(payload, tenant_id="tenant_demo")

    assert event["payload"]["status"] == "cancelled"
    assert event["payload"]["text"].startswith("[Cancelled]")


def test_google_calendar_connector_fetch_seeded_events() -> None:
    connector = GoogleCalendarConnector(
        tenant_id="tenant_demo",
        seeded_events=[
            {
                "id": "evt-123",
                "summary": "Daily Incident Sync",
                "organizer": {"email": "ops@example.com"},
                "start": {"dateTime": "2026-07-01T11:30:00Z"},
            }
        ],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "google-calendar-event-evt-123"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"


def test_google_calendar_connector_retries_and_succeeds(monkeypatch) -> None:
    connector = GoogleCalendarConnector(
        tenant_id="tenant_demo",
        token="calendar-token",
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
                "id": "evt-999",
                "summary": "Recovered fetch",
                "start": {"dateTime": "2026-07-01T11:30:00Z"},
            }
        ]

    monkeypatch.setattr(connector, "_fetch_events_from_api", flaky_fetch)

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert attempts["count"] == 3
    assert connector.last_retry_count == 2


def test_google_calendar_connector_retries_and_fails(monkeypatch) -> None:
    connector = GoogleCalendarConnector(
        tenant_id="tenant_demo",
        token="calendar-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def always_fail() -> list[dict[str, str]]:
        attempts["count"] += 1
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(connector, "_fetch_events_from_api", always_fail)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        list(connector.fetch_events())

    assert attempts["count"] == 3
    assert connector.last_retry_count == 2


def test_google_calendar_connector_does_not_retry_on_401(monkeypatch) -> None:
    connector = GoogleCalendarConnector(
        tenant_id="tenant_demo",
        token="calendar-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def unauthorized() -> list[dict[str, str]]:
        attempts["count"] += 1
        raise _http_status_error(401)

    monkeypatch.setattr(connector, "_fetch_events_from_api", unauthorized)

    with pytest.raises(httpx.HTTPStatusError):
        list(connector.fetch_events())

    assert attempts["count"] == 1
    assert connector.last_retry_count == 0


def test_google_calendar_connector_retries_on_429(monkeypatch) -> None:
    connector = GoogleCalendarConnector(
        tenant_id="tenant_demo",
        token="calendar-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def rate_limited() -> list[dict[str, str]]:
        attempts["count"] += 1
        raise _http_status_error(429)

    monkeypatch.setattr(connector, "_fetch_events_from_api", rate_limited)

    with pytest.raises(httpx.HTTPStatusError):
        list(connector.fetch_events())

    assert attempts["count"] == 3
    assert connector.last_retry_count == 2
