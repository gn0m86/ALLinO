from app.connectors.slack_connector import SlackConnector, map_slack_message_to_unified_event


def test_map_slack_message_to_unified_event() -> None:
    message = {
        "ts": "1780000100.000200",
        "text": "Build failed on main",
        "user": "U123",
        "channel": "COPS",
    }

    event = map_slack_message_to_unified_event(
        message,
        tenant_id="tenant_demo",
        channel_id="COPS",
    )

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "slack"
    assert event["externalId"] == "COPS:1780000100.000200"
    assert "Build failed on main" in event["payload"]["text"]


def test_slack_connector_fetch_seeded_events() -> None:
    connector = SlackConnector(
        tenant_id="tenant_demo",
        channel_id="COPS",
        seeded_messages=[
            {
                "ts": "1780000100.000200",
                "text": "hello",
                "user": "U123",
                "channel": "COPS",
            }
        ],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "slack-message-COPS:1780000100.000200"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"
