import pytest
import httpx

from app.connectors.base import RetryPolicy
from app.connectors.teams_connector import TeamsConnector, map_teams_message_to_unified_event


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://graph.microsoft.com/v1.0/me/chats")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError("provider error", request=request, response=response)


def test_map_teams_message_to_unified_event() -> None:
    payload = {
        "id": "msg-100",
        "chatId": "chat-1",
        "createdDateTime": "2026-07-01T13:00:00Z",
        "body": {"content": "prod deploy approved"},
        "from": {"user": {"displayName": "Ops Bot"}},
        "webUrl": "https://teams.microsoft.com/l/message/msg-100",
    }

    event = map_teams_message_to_unified_event(payload, tenant_id="tenant_demo")

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "teams"
    assert event["externalId"] == "chat-1:msg-100"
    assert "prod deploy approved" in event["payload"]["text"]


def test_teams_connector_fetch_seeded_events() -> None:
    connector = TeamsConnector(
        tenant_id="tenant_demo",
        seeded_messages=[
            {
                "id": "msg-100",
                "chatId": "chat-1",
                "createdDateTime": "2026-07-01T13:00:00Z",
                "body": {"content": "prod deploy approved"},
                "from": {"user": {"displayName": "Ops Bot"}},
            }
        ],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "teams-message-chat-1:msg-100"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"


def test_teams_connector_retries_and_succeeds(monkeypatch) -> None:
    connector = TeamsConnector(
        tenant_id="tenant_demo",
        token="teams-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def flaky_fetch() -> list[dict[str, object]]:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient graph error")
        return [
            {
                "id": "msg-r1",
                "chatId": "chat-r",
                "createdDateTime": "2026-07-01T13:00:00Z",
                "body": {"content": "recovered"},
                "from": {"user": {"displayName": "Ops Bot"}},
            }
        ]

    monkeypatch.setattr(connector, "_fetch_messages_from_api", flaky_fetch)

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert attempts["count"] == 3
    assert connector.last_retry_count == 2


def test_teams_connector_retries_and_fails(monkeypatch) -> None:
    connector = TeamsConnector(
        tenant_id="tenant_demo",
        token="teams-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def always_fail() -> list[dict[str, object]]:
        attempts["count"] += 1
        raise RuntimeError("graph unavailable")

    monkeypatch.setattr(connector, "_fetch_messages_from_api", always_fail)

    with pytest.raises(RuntimeError, match="graph unavailable"):
        list(connector.fetch_events())

    assert attempts["count"] == 3
    assert connector.last_retry_count == 2


def test_teams_connector_does_not_retry_on_401(monkeypatch) -> None:
    connector = TeamsConnector(
        tenant_id="tenant_demo",
        token="teams-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def unauthorized() -> list[dict[str, object]]:
        attempts["count"] += 1
        raise _http_status_error(401)

    monkeypatch.setattr(connector, "_fetch_messages_from_api", unauthorized)

    with pytest.raises(httpx.HTTPStatusError):
        list(connector.fetch_events())

    assert attempts["count"] == 1
    assert connector.last_retry_count == 0


def test_teams_connector_retries_on_500(monkeypatch) -> None:
    connector = TeamsConnector(
        tenant_id="tenant_demo",
        token="teams-token",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    connector.start()

    attempts = {"count": 0}

    def service_unavailable() -> list[dict[str, object]]:
        attempts["count"] += 1
        raise _http_status_error(503)

    monkeypatch.setattr(connector, "_fetch_messages_from_api", service_unavailable)

    with pytest.raises(httpx.HTTPStatusError):
        list(connector.fetch_events())

    assert attempts["count"] == 3
    assert connector.last_retry_count == 2
