import pytest
import httpx

from app.connectors.base import RetryPolicy
from app.connectors.rocketchat_connector import (
    RocketChatConnector,
    get_dm_counterpart_utc_offset,
    get_own_rocketchat_username,
    map_rocketchat_message_to_unified_event,
)


def _http_status_error(status_code: int, headers: dict | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://chat.example.com/api/v1/channels.messages")
    response = httpx.Response(status_code=status_code, request=request, headers=headers or {})
    return httpx.HTTPStatusError("provider error", request=request, response=response)


def _connector(**overrides) -> RocketChatConnector:
    defaults = dict(
        tenant_id="tenant_demo",
        token="rc-token",
        user_id="rc-user",
        base_url="https://chat.example.com",
        channel_id="GENERAL",
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )
    defaults.update(overrides)
    return RocketChatConnector(**defaults)


def test_map_rocketchat_message_to_unified_event() -> None:
    message = {
        "_id": "3001",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "deploy finished",
        "rid": "GENERAL",
        "u": {"username": "ops-bot"},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "rocketchat"
    assert event["externalId"] == "GENERAL:3001"
    assert "deploy finished" in event["payload"]["text"]
    # Thread grouping anchor is the stable room id, not the message-unique
    # external_id -- see the Sprint 31 regression tests in test_thread_key.py.
    assert event["payload"]["identifier"] == "GENERAL"
    # Defaults to "channel" when the caller doesn't know the room's team status
    # (e.g. single-room mode, which skips the extra channels.info/groups.info lookup).
    assert event["payload"]["channel_kind"] == "channel"
    assert event["payload"]["channel_team"] is None


def test_map_rocketchat_message_prefers_display_name_over_username() -> None:
    """The channel-browser list already shows display names (subscriptions.get's
    fname) -- the transcript's per-message sender should match, not fall back to
    showing the technical username just because that's what's easiest to read
    off the message payload."""
    message = {
        "_id": "3006",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "hello",
        "rid": "GENERAL",
        "u": {"username": "sergey.markov", "name": "Сергій Марков"},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert event["payload"]["sender"] == "Сергій Марков"


def test_map_rocketchat_message_falls_back_to_username_without_display_name() -> None:
    message = {
        "_id": "3007",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "automated notice",
        "rid": "GENERAL",
        "u": {"username": "ops-bot"},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert event["payload"]["sender"] == "ops-bot"


def test_map_rocketchat_message_carries_explicit_channel_kind_and_team() -> None:
    message = {
        "_id": "3005",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "team update",
        "rid": "team-room-1",
        "u": {"username": "vik"},
    }

    event = map_rocketchat_message_to_unified_event(
        message,
        tenant_id="tenant_demo",
        channel_kind="team",
        channel_team="developer_department",
    )

    assert event["payload"]["channel_kind"] == "team"
    assert event["payload"]["channel_team"] == "developer_department"


def test_map_rocketchat_message_strips_empty_label_markdown_links() -> None:
    """Rocket.Chat's "jump to message" quote links commonly render as an
    empty-label markdown link, e.g. [ ](https://.../msg?...) -- that should
    disappear entirely rather than showing as raw markdown noise."""
    message = {
        "_id": "3002",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "[ ](https://rc.example.com/channel/General/msg?msg=abc123) Please remember to update.",
        "rid": "GENERAL",
        "u": {"username": "vik"},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert "https://rc.example.com" not in event["payload"]["text"]
    assert "Please remember to update." in event["payload"]["text"]


def test_map_rocketchat_message_keeps_markdown_link_label() -> None:
    message = {
        "_id": "3003",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "See [the release notes](https://rc.example.com/notes) for details",
        "rid": "GENERAL",
        "u": {"username": "vik"},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert "https://rc.example.com" not in event["payload"]["text"]
    assert "the release notes" in event["payload"]["text"]


def test_map_rocketchat_message_extracts_image_attachment() -> None:
    message = {
        "_id": "4001",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "",
        "rid": "GENERAL",
        "u": {"username": "vik"},
        "file": {"_id": "fileId123", "name": "photo.jpg", "type": "image/jpeg", "size": 37936},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert event["payload"]["attachment_ref"] == "fileId123"
    assert event["payload"]["attachment_type"] == "image"
    assert event["payload"]["attachment_size"] == 37936
    # A file with no text body still gets a non-empty preview, so it's not
    # invisible in the inbox list.
    assert event["payload"]["text"]


def test_map_rocketchat_message_extracts_video_attachment() -> None:
    message = {
        "_id": "4002",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "check this out",
        "rid": "GENERAL",
        "u": {"username": "vik"},
        "files": [{"_id": "fileId456", "name": "clip.mp4", "type": "video/mp4"}],
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert event["payload"]["attachment_ref"] == "fileId456"
    assert event["payload"]["attachment_type"] == "video"


def test_map_rocketchat_message_captures_thread_root_id() -> None:
    message = {
        "_id": "4005",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "sure, will do",
        "rid": "GENERAL",
        "u": {"username": "vik"},
        "tmid": "rootMsg123",
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert event["payload"]["reply_to_message_id"] == "rootMsg123"


def test_map_rocketchat_message_without_tmid_has_no_reply_target() -> None:
    message = {
        "_id": "4006",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "starting a new topic",
        "rid": "GENERAL",
        "u": {"username": "vik"},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert event["payload"]["reply_to_message_id"] is None


def test_map_rocketchat_message_treats_non_media_file_as_generic_file() -> None:
    message = {
        "_id": "4003",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "see attached",
        "rid": "GENERAL",
        "u": {"username": "vik"},
        "file": {"_id": "fileId789", "name": "report.pdf", "type": "application/pdf"},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert event["payload"]["attachment_ref"] == "fileId789"
    assert event["payload"]["attachment_type"] == "file"
    assert event["payload"]["attachment_name"] == "report.pdf"


def test_map_rocketchat_message_without_file_has_no_attachment() -> None:
    message = {
        "_id": "4004",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "just text",
        "rid": "GENERAL",
        "u": {"username": "vik"},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_id="GENERAL")

    assert event["payload"]["attachment_ref"] is None
    assert event["payload"]["attachment_type"] is None


def test_map_rocketchat_message_prefers_channel_name_for_display() -> None:
    """Room ids from Rocket.Chat are often opaque hashes -- when a human-readable
    name is available (from subscriptions.get in "all rooms" mode), it should be
    shown instead, while grouping still anchors on the stable room id."""
    message = {
        "_id": "3001",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "hello team",
        "rid": "aBc123HashLikeId",
        "u": {"username": "vik"},
    }

    event = map_rocketchat_message_to_unified_event(message, tenant_id="tenant_demo", channel_name="TorgSoft")

    assert event["payload"]["channel"] == "TorgSoft"
    assert "TorgSoft" in event["payload"]["text"]
    assert event["payload"]["identifier"] == "aBc123HashLikeId"


def test_map_rocketchat_message_requires_id() -> None:
    with pytest.raises(ValueError):
        map_rocketchat_message_to_unified_event({}, tenant_id="tenant_demo")


def test_rocketchat_connector_fetch_seeded_events() -> None:
    connector = RocketChatConnector(
        tenant_id="tenant_demo",
        channel_id="GENERAL",
        seeded_messages=[
            {
                "_id": "3001",
                "ts": "2026-07-02T12:10:00Z",
                "msg": "hello",
                "rid": "GENERAL",
                "u": {"username": "ops-bot"},
            }
        ],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "rocketchat-message-GENERAL:3001"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"


def test_rocketchat_connector_degraded_without_credentials() -> None:
    connector = RocketChatConnector(tenant_id="tenant_demo")
    connector.start()

    assert connector.health().status == "degraded"


def test_rocketchat_connector_healthy_without_channel_id() -> None:
    """channel_id is optional -- token+user_id+base_url alone is enough to be
    healthy, since omitting it means "watch every room" rather than
    "misconfigured"."""
    connector = RocketChatConnector(
        tenant_id="tenant_demo",
        token="rc-token",
        user_id="rc-user",
        base_url="https://chat.example.com",
    )
    connector.start()

    assert connector.health().status == "healthy"


def test_rocketchat_connector_fetches_all_subscribed_rooms(monkeypatch) -> None:
    connector = _connector(channel_id=None)
    connector.start()
    monkeypatch.setattr("app.connectors.rocketchat_connector.time.sleep", lambda _seconds: None)

    calls: list[tuple[str, dict]] = []

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            calls.append((url, params or {}))
            if url.endswith("/subscriptions.get"):
                return FakeResponse(
                    {
                        "update": [
                            {"rid": "GENERAL", "t": "c", "name": "general"},
                            {"rid": "priv1", "t": "p", "name": "private-room"},
                            {"rid": "dm1", "t": "d", "name": "direct-message"},
                        ]
                    }
                )
            if url.endswith("/channels.messages"):
                return FakeResponse({"messages": [{"_id": "m1", "msg": "public msg", "rid": "GENERAL", "u": {}}]})
            if url.endswith("/groups.messages"):
                return FakeResponse({"messages": [{"_id": "m2", "msg": "private msg", "rid": "priv1", "u": {}}]})
            if url.endswith("/im.messages"):
                return FakeResponse({"messages": [{"_id": "m3", "msg": "dm msg", "rid": "dm1", "u": {}}]})
            if url.endswith("/channels.info"):
                return FakeResponse({"channel": {"teamMain": False}})
            if url.endswith("/groups.info"):
                return FakeResponse({"group": {"teamMain": False}})
            raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    events = list(connector.fetch_events())

    assert {e["externalId"] for e in events} == {"GENERAL:m1", "priv1:m2", "dm1:m3"}
    requested_urls = [url for url, _ in calls]
    assert requested_urls[0].endswith("/subscriptions.get")
    assert any(u.endswith("/channels.messages") for u in requested_urls)
    assert any(u.endswith("/groups.messages") for u in requested_urls)
    assert any(u.endswith("/im.messages") for u in requested_urls)

    # Each event's displayed channel comes from subscriptions.get's room name,
    # not the raw (often opaque) room id.
    by_external_id = {e["externalId"]: e for e in events}
    assert by_external_id["GENERAL:m1"]["payload"]["channel"] == "general"
    assert by_external_id["priv1:m2"]["payload"]["channel"] == "private-room"
    assert by_external_id["dm1:m3"]["payload"]["channel"] == "direct-message"

    # Room kind: "c"/"p" rooms default to "channel" (teamMain=False in this fake
    # response), "d" is always "dm" without needing an info lookup.
    assert by_external_id["GENERAL:m1"]["payload"]["channel_kind"] == "channel"
    assert by_external_id["priv1:m2"]["payload"]["channel_kind"] == "channel"
    assert by_external_id["dm1:m3"]["payload"]["channel_kind"] == "dm"
    assert any(u.endswith("/channels.info") for u in requested_urls)
    assert any(u.endswith("/groups.info") for u in requested_urls)


def test_rocketchat_connector_detects_team_main_channel(monkeypatch) -> None:
    connector = _connector(channel_id=None)
    connector.start()
    monkeypatch.setattr("app.connectors.rocketchat_connector.time.sleep", lambda _seconds: None)

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            if url.endswith("/subscriptions.get"):
                return FakeResponse({"update": [{"rid": "team-room-1", "t": "p", "name": "developer_department"}]})
            if url.endswith("/groups.messages"):
                return FakeResponse({"messages": [{"_id": "m1", "msg": "hi team", "rid": "team-room-1", "u": {}}]})
            if url.endswith("/groups.info"):
                return FakeResponse({"group": {"teamMain": True, "fname": "developer_department"}})
            raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["payload"]["channel_kind"] == "team"
    assert events[0]["payload"]["channel_team"] == "developer_department"


def test_rocketchat_connector_skips_rooms_with_unknown_type(monkeypatch) -> None:
    connector = _connector(channel_id=None)
    connector.start()

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            if url.endswith("/subscriptions.get"):
                return FakeResponse({"update": [{"rid": "weird1", "t": "l"}]})
            raise AssertionError(f"unexpected url for unknown room type: {url}")

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    events = list(connector.fetch_events())

    assert events == []


def test_rocketchat_connector_retries_and_succeeds(monkeypatch) -> None:
    connector = _connector()
    connector.start()

    attempts = {"count": 0}

    def flaky_fetch() -> list[dict[str, str]]:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient provider error")
        return [
            {
                "_id": "3999",
                "ts": "2026-07-02T12:10:00Z",
                "msg": "recovered fetch",
                "rid": "GENERAL",
                "u": {"username": "ops-bot"},
            }
        ]

    monkeypatch.setattr(connector, "_fetch_messages_from_api", flaky_fetch)

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert attempts["count"] == 3
    assert connector.last_retry_count == 2


def test_rocketchat_connector_retries_and_fails(monkeypatch) -> None:
    connector = _connector()
    connector.start()

    attempts = {"count": 0}

    def always_fail() -> list[dict[str, str]]:
        attempts["count"] += 1
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(connector, "_fetch_messages_from_api", always_fail)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        list(connector.fetch_events())

    assert attempts["count"] == 3
    assert connector.last_retry_count == 2


def test_rocketchat_connector_does_not_retry_on_401(monkeypatch) -> None:
    connector = _connector()
    connector.start()

    attempts = {"count": 0}

    def unauthorized() -> list[dict[str, str]]:
        attempts["count"] += 1
        raise _http_status_error(401)

    monkeypatch.setattr(connector, "_fetch_messages_from_api", unauthorized)

    with pytest.raises(httpx.HTTPStatusError):
        list(connector.fetch_events())

    assert attempts["count"] == 1
    assert connector.last_retry_count == 0


def test_rocketchat_connector_retries_on_429(monkeypatch) -> None:
    connector = _connector()
    connector.start()

    attempts = {"count": 0}

    def rate_limited() -> list[dict[str, str]]:
        attempts["count"] += 1
        raise _http_status_error(429)

    monkeypatch.setattr(connector, "_fetch_messages_from_api", rate_limited)

    with pytest.raises(httpx.HTTPStatusError):
        list(connector.fetch_events())

    assert attempts["count"] == 3
    assert connector.last_retry_count == 2


def test_fetch_room_messages_recovers_after_one_429(monkeypatch) -> None:
    connector = _connector(channel_id=None)
    connector.start()

    monkeypatch.setattr("app.connectors.rocketchat_connector.time.sleep", lambda _seconds: None)

    calls = {"count": 0}

    def flaky_get_once(client, endpoint, room_id):
        calls["count"] += 1
        if calls["count"] == 1:
            raise _http_status_error(429, headers={"Retry-After": "1"})
        return [{"_id": "m1", "msg": "recovered", "rid": room_id, "u": {}}]

    monkeypatch.setattr(connector, "_get_room_messages_once", flaky_get_once)

    result = connector._fetch_room_messages(object(), "GENERAL", "c")

    assert calls["count"] == 2
    assert result == [{"_id": "m1", "msg": "recovered", "rid": "GENERAL", "u": {}}]


def test_fetch_room_messages_gives_up_after_persistent_429(monkeypatch) -> None:
    connector = _connector(channel_id=None)
    connector.start()

    monkeypatch.setattr("app.connectors.rocketchat_connector.time.sleep", lambda _seconds: None)

    def always_rate_limited(client, endpoint, room_id):
        raise _http_status_error(429)

    monkeypatch.setattr(connector, "_get_room_messages_once", always_rate_limited)

    result = connector._fetch_room_messages(object(), "GENERAL", "c")

    assert result == []


def test_fetch_room_messages_raises_on_non_429_error(monkeypatch) -> None:
    connector = _connector(channel_id=None)
    connector.start()

    def unauthorized(client, endpoint, room_id):
        raise _http_status_error(401)

    monkeypatch.setattr(connector, "_get_room_messages_once", unauthorized)

    with pytest.raises(httpx.HTTPStatusError):
        connector._fetch_room_messages(object(), "GENERAL", "c")


def test_all_rooms_sync_skips_rate_limited_room_but_returns_others(monkeypatch) -> None:
    connector = _connector(channel_id=None)
    connector.start()

    monkeypatch.setattr("app.connectors.rocketchat_connector.time.sleep", lambda _seconds: None)

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            if url.endswith("/subscriptions.get"):
                return FakeResponse(
                    {
                        "update": [
                            {"rid": "busy-room", "t": "c"},
                            {"rid": "GENERAL", "t": "c"},
                        ]
                    }
                )
            if (params or {}).get("roomId") == "busy-room":
                raise _http_status_error(429)
            return FakeResponse({"messages": [{"_id": "m1", "msg": "ok", "rid": "GENERAL", "u": {}}]})

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    events = list(connector.fetch_events())

    assert {e["externalId"] for e in events} == {"GENERAL:m1"}


class _FakeOffsetResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_get_dm_counterpart_utc_offset_returns_offset(monkeypatch) -> None:
    calls: list[tuple[str, dict | None]] = []

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            calls.append((url, params))
            if url.endswith("/subscriptions.get"):
                return _FakeOffsetResponse(
                    {"update": [{"rid": "dm1", "t": "d", "name": "counterpart-user"}, {"rid": "other", "t": "c"}]}
                )
            if url.endswith("/users.info"):
                assert params == {"username": "counterpart-user"}
                return _FakeOffsetResponse({"user": {"utcOffset": -5}, "success": True})
            raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    offset = get_dm_counterpart_utc_offset(
        token="rc-token", user_id="rc-user", base_url="https://chat.example.com", room_id="dm1"
    )

    assert offset == -5


def test_get_dm_counterpart_utc_offset_returns_none_for_non_dm_room(monkeypatch) -> None:
    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            if url.endswith("/subscriptions.get"):
                return _FakeOffsetResponse({"update": [{"rid": "GENERAL", "t": "c", "name": "general"}]})
            raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    offset = get_dm_counterpart_utc_offset(
        token="rc-token", user_id="rc-user", base_url="https://chat.example.com", room_id="GENERAL"
    )

    assert offset is None


def test_get_dm_counterpart_utc_offset_returns_none_on_lookup_failure(monkeypatch) -> None:
    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    offset = get_dm_counterpart_utc_offset(
        token="rc-token", user_id="rc-user", base_url="https://chat.example.com", room_id="dm1"
    )

    assert offset is None


def test_get_own_rocketchat_username_prefers_display_name(monkeypatch) -> None:
    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            assert url.endswith("/me")
            return _FakeOffsetResponse({"username": "mikhail.chernikov", "name": "Mykhailo Chernikov"})

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    name = get_own_rocketchat_username(token="rc-token", user_id="rc-user", base_url="https://chat.example.com")

    assert name == "Mykhailo Chernikov"


def test_get_own_rocketchat_username_falls_back_to_username(monkeypatch) -> None:
    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            return _FakeOffsetResponse({"username": "ops-bot"})

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    name = get_own_rocketchat_username(token="rc-token", user_id="rc-user", base_url="https://chat.example.com")

    assert name == "ops-bot"


def test_get_own_rocketchat_username_returns_none_on_failure(monkeypatch) -> None:
    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params: dict | None = None, headers: dict | None = None):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr("app.connectors.rocketchat_connector.httpx.Client", lambda timeout=10.0: FakeClient())

    name = get_own_rocketchat_username(token="rc-token", user_id="rc-user", base_url="https://chat.example.com")

    assert name is None
