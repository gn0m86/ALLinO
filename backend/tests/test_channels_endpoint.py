from fastapi.testclient import TestClient

from app.db import session
from app.main import app


def _seed_chat_message(
    client: TestClient,
    event_id: str,
    channel_kind: str,
    rid: str = "GENERAL",
    text: str = "hello",
    tenant_id: str = "tenant_demo",
    channel_team: str | None = None,
    timestamp: str = "2026-07-03T12:00:00Z",
) -> None:
    payload: dict = {"text": f"{rid} | someone | {text}", "identifier": rid, "channel_kind": channel_kind}
    if channel_team:
        payload["channel_team"] = channel_team
    resp = client.post(
        f"/api/v1/ingestion/events?tenant_id={tenant_id}",
        json={
            "eventId": event_id,
            "tenantId": tenant_id,
            "sourceType": "rocketchat",
            "externalId": f"{rid}:{event_id}",
            "timestamp": timestamp,
            "payload": payload,
            "schemaVersion": "1.0.0",
        },
    )
    assert resp.status_code == 200


def test_channels_endpoint_returns_one_row_per_channel(tmp_path) -> None:
    session.DB_PATH = tmp_path / "channels_group.db"

    with TestClient(app) as client:
        _seed_chat_message(client, "m1", "channel", rid="GENERAL", text="first", timestamp="2026-07-03T12:00:00Z")
        _seed_chat_message(client, "m2", "channel", rid="GENERAL", text="second", timestamp="2026-07-03T12:05:00Z")
        _seed_chat_message(client, "m3", "dm", rid="dm-room", text="hi", timestamp="2026-07-03T12:01:00Z")

        resp = client.get("/api/v1/ingestion/channels?tenant_id=tenant_demo")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        general = next(c for c in data if c["latest"]["external_id"].startswith("GENERAL"))
        assert "second" in general["latest"]["preview"]
        assert general["channel_kind"] == "channel"


def test_channels_endpoint_excludes_non_chat_sources(tmp_path) -> None:
    session.DB_PATH = tmp_path / "channels_exclude_non_chat.db"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/events?tenant_id=tenant_demo",
            json={
                "eventId": "gh-1",
                "tenantId": "tenant_demo",
                "sourceType": "github",
                "externalId": "gh-1",
                "timestamp": "2026-07-03T12:00:00Z",
                "payload": {"text": "a PR"},
                "schemaVersion": "1.0.0",
            },
        )
        assert resp.status_code == 200
        _seed_chat_message(client, "m1", "channel", rid="GENERAL")

        resp = client.get("/api/v1/ingestion/channels?tenant_id=tenant_demo")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "rocketchat"


def test_channels_endpoint_filters_by_source(tmp_path) -> None:
    session.DB_PATH = tmp_path / "channels_filter_source.db"

    with TestClient(app) as client:
        _seed_chat_message(client, "m1", "channel", rid="GENERAL")

        resp = client.get("/api/v1/ingestion/channels?tenant_id=tenant_demo&source=slack")
        assert resp.status_code == 200
        assert resp.json() == []

        resp = client.get("/api/v1/ingestion/channels?tenant_id=tenant_demo&source=rocketchat")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


def test_channels_endpoint_is_tenant_scoped(tmp_path) -> None:
    session.DB_PATH = tmp_path / "channels_tenant_scoped.db"

    with TestClient(app) as client:
        _seed_chat_message(client, "m1", "channel", rid="GENERAL", tenant_id="tenant_a")
        _seed_chat_message(client, "m2", "channel", rid="GENERAL", tenant_id="tenant_b")

        resp_a = client.get("/api/v1/ingestion/channels?tenant_id=tenant_a")
        assert len(resp_a.json()) == 1

        resp_b = client.get("/api/v1/ingestion/channels?tenant_id=tenant_b")
        assert len(resp_b.json()) == 1


def test_channel_unread_until_marked_read(tmp_path) -> None:
    session.DB_PATH = tmp_path / "channels_unread.db"

    with TestClient(app) as client:
        _seed_chat_message(client, "m1", "channel", rid="GENERAL")

        resp = client.get("/api/v1/ingestion/channels?tenant_id=tenant_demo")
        data = resp.json()
        assert len(data) == 1
        thread_key = data[0]["thread_key"]
        assert data[0]["unread"] is True

        resp = client.post(f"/api/v1/ingestion/threads/{thread_key}/read?tenant_id=tenant_demo")
        assert resp.status_code == 200

        resp = client.get("/api/v1/ingestion/channels?tenant_id=tenant_demo")
        data = resp.json()
        assert data[0]["unread"] is False


def test_new_message_after_read_marks_channel_unread_again(tmp_path) -> None:
    session.DB_PATH = tmp_path / "channels_unread_again.db"

    with TestClient(app) as client:
        _seed_chat_message(client, "m1", "channel", rid="GENERAL", timestamp="2026-07-03T12:00:00Z")

        resp = client.get("/api/v1/ingestion/channels?tenant_id=tenant_demo")
        thread_key = resp.json()[0]["thread_key"]

        resp = client.post(f"/api/v1/ingestion/threads/{thread_key}/read?tenant_id=tenant_demo")
        assert resp.status_code == 200

        # A new message with a timestamp far in the future is unambiguously "after"
        # the read marker (which was just set to "now").
        _seed_chat_message(client, "m2", "channel", rid="GENERAL", timestamp="2027-01-01T00:00:00Z")

        resp = client.get("/api/v1/ingestion/channels?tenant_id=tenant_demo")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["unread"] is True


def test_thread_messages_endpoint_returns_chronological_order(tmp_path) -> None:
    session.DB_PATH = tmp_path / "thread_messages_order.db"

    with TestClient(app) as client:
        _seed_chat_message(client, "m1", "channel", rid="GENERAL", text="first", timestamp="2026-07-03T12:00:00Z")
        _seed_chat_message(client, "m2", "channel", rid="GENERAL", text="second", timestamp="2026-07-03T12:05:00Z")
        _seed_chat_message(client, "m3", "channel", rid="GENERAL", text="third", timestamp="2026-07-03T12:10:00Z")

        resp = client.get("/api/v1/ingestion/channels?tenant_id=tenant_demo")
        thread_key = resp.json()[0]["thread_key"]

        resp = client.get(f"/api/v1/ingestion/threads/{thread_key}/messages?tenant_id=tenant_demo")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        previews = [m["preview"] for m in data]
        assert "first" in previews[0]
        assert "second" in previews[1]
        assert "third" in previews[2]


def test_dm_timezone_endpoint_returns_null_when_rocketchat_not_configured(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "dm_timezone_not_configured.db"
    monkeypatch.delenv("ALLINO_ROCKETCHAT_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_ROCKETCHAT_USER_ID", raising=False)
    monkeypatch.delenv("ALLINO_ROCKETCHAT_BASE_URL", raising=False)

    with TestClient(app) as client:
        resp = client.get("/api/v1/ingestion/rocketchat/dm-timezone?room_id=dm1&tenant_id=tenant_demo")
        assert resp.status_code == 200
        assert resp.json() == {"utc_offset_hours": None}


def test_dm_timezone_endpoint_returns_offset_when_configured(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "dm_timezone_configured.db"
    monkeypatch.setenv("ALLINO_ROCKETCHAT_TOKEN", "rc-token")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_USER_ID", "rc-user")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_BASE_URL", "https://chat.example.com")

    import app.api.channels as channels_module

    monkeypatch.setattr(
        channels_module,
        "get_dm_counterpart_utc_offset",
        lambda **kwargs: -5,
    )

    with TestClient(app) as client:
        resp = client.get("/api/v1/ingestion/rocketchat/dm-timezone?room_id=dm1&tenant_id=tenant_demo")
        assert resp.status_code == 200
        assert resp.json() == {"utc_offset_hours": -5}
