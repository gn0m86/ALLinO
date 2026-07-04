from app.connectors.telegram_connector import TelegramConnector, map_telegram_update_to_unified_event


def test_map_telegram_update_to_unified_event() -> None:
    update = {
        "update_id": 9001,
        "message": {
            "message_id": 101,
            "date": 1780000000,
            "text": "Deploy failed in prod",
            "chat": {"id": -100123, "title": "Ops Alerts"},
            "from": {"username": "alerts_bot"},
        },
    }

    event = map_telegram_update_to_unified_event(update, tenant_id="tenant_demo")

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "telegram"
    assert event["eventId"] == "tg-update-9001"
    assert event["externalId"] == "-100123:101"
    assert "Ops Alerts" in event["payload"]["text"]
    assert event["payload"]["channel_kind"] is None


def test_map_telegram_update_classifies_private_chat_as_dm() -> None:
    update = {
        "update_id": 9010,
        "message": {
            "message_id": 200,
            "date": 1780000000,
            "text": "hi",
            "chat": {"id": 555, "type": "private", "first_name": "Alex"},
            "from": {"username": "alex"},
        },
    }

    event = map_telegram_update_to_unified_event(update, tenant_id="tenant_demo")

    assert event["payload"]["channel_kind"] == "dm"


def test_map_telegram_update_classifies_group_and_supergroup_and_channel_as_channel() -> None:
    for chat_type in ("group", "supergroup", "channel"):
        update = {
            "update_id": 9011,
            "message": {
                "message_id": 201,
                "date": 1780000000,
                "text": "hi",
                "chat": {"id": -100999, "type": chat_type, "title": "Ops"},
            },
        }

        event = map_telegram_update_to_unified_event(update, tenant_id="tenant_demo")

        assert event["payload"]["channel_kind"] == "channel"


def test_telegram_connector_fetch_seeded_events() -> None:
    connector = TelegramConnector(
        tenant_id="tenant_demo",
        seeded_updates=[
            {
                "update_id": 9002,
                "message": {
                    "message_id": 102,
                    "text": "hello",
                    "chat": {"id": -100123, "title": "Ops Alerts"},
                },
            }
        ],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "tg-update-9002"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"
