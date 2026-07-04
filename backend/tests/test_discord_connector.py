from app.connectors.discord_connector import DiscordConnector, map_discord_message_to_unified_event


def test_map_discord_message_to_unified_event() -> None:
    message = {
        "id": "2001",
        "timestamp": "2026-07-01T12:10:00Z",
        "content": "API latency spike",
        "channel_id": "987",
        "author": {"username": "ops-bot"},
    }

    event = map_discord_message_to_unified_event(
        message,
        tenant_id="tenant_demo",
        channel_id="987",
    )

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "discord"
    assert event["externalId"] == "987:2001"
    assert "API latency spike" in event["payload"]["text"]


def test_discord_connector_fetch_seeded_events() -> None:
    connector = DiscordConnector(
        tenant_id="tenant_demo",
        channel_id="987",
        seeded_messages=[
            {
                "id": "2001",
                "timestamp": "2026-07-01T12:10:00Z",
                "content": "hello",
                "channel_id": "987",
                "author": {"username": "ops-bot"},
            }
        ],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "discord-message-987:2001"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"
