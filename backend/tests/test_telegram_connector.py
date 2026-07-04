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
