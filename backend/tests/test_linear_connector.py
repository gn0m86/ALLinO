from app.connectors.linear_connector import LinearConnector, map_linear_event_to_unified_event


def test_map_linear_event_to_unified_event() -> None:
    payload = {
        "id": "lin-1",
        "identifier": "ENG-42",
        "title": "Fix login bug",
        "url": "https://linear.app/org/issue/ENG-42",
        "createdAt": "2026-06-25T09:00:00Z",
        "state": {"name": "In Progress"},
        "team": {"key": "ENG"},
    }

    event = map_linear_event_to_unified_event(payload, tenant_id="tenant_demo")

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "linear"
    assert event["externalId"] == "lin-1"
    assert event["schemaVersion"] == "1.0.0"
    assert "ENG" in event["payload"]["text"]
    assert "Fix login bug" in event["payload"]["text"]


def test_linear_connector_fetch_seeded_events() -> None:
    connector = LinearConnector(
        tenant_id="tenant_demo",
        seeded_events=[{"id": "lin-seeded-1", "title": "Issue seeded", "team": {"key": "ENG"}}],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "linear-issue-lin-seeded-1"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"
