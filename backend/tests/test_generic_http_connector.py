from app.connectors.generic_http_connector import (
    GenericHttpConnector,
    extract_items_from_payload,
    extract_path,
    map_generic_item_to_unified_event,
)

FIELD_MAPPING = {"externalId": "id", "timestamp": "updated_at", "preview": "title"}


def test_extract_path_nested() -> None:
    item = {"data": {"id": "42"}}
    assert extract_path(item, "data.id") == "42"
    assert extract_path(item, "data.missing") is None
    assert extract_path(item, "missing.path") is None


def test_extract_path_array_index() -> None:
    item = {"contacts": [{"profile": {"name": "Alice"}}]}
    assert extract_path(item, "contacts.0.profile.name") == "Alice"
    assert extract_path(item, "contacts.5.profile.name") is None
    assert extract_path(item, "contacts.not-a-number") is None


def test_extract_items_from_payload_variants() -> None:
    assert extract_items_from_payload([{"id": 1}, {"id": 2}]) == [{"id": 1}, {"id": 2}]
    assert extract_items_from_payload({"items": [{"id": 1}]}) == [{"id": 1}]
    assert extract_items_from_payload({"data": [{"id": 1}]}) == [{"id": 1}]
    assert extract_items_from_payload({"results": [{"id": 1}]}) == [{"id": 1}]
    assert extract_items_from_payload({"id": 1}) == [{"id": 1}]
    assert extract_items_from_payload("not a payload") == []


def test_extract_items_from_payload_with_items_path_whatsapp_shaped() -> None:
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-1",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"id": "wamid.1", "text": {"body": "hi"}},
                                {"id": "wamid.2", "text": {"body": "there"}},
                            ]
                        },
                        "field": "messages",
                    }
                ],
            },
            {
                "id": "entry-2",
                "changes": [{"value": {"messages": [{"id": "wamid.3", "text": {"body": "again"}}]}}],
            },
        ],
    }

    items = extract_items_from_payload(payload, "entry[].changes[].value.messages[]")

    assert [item["id"] for item in items] == ["wamid.1", "wamid.2", "wamid.3"]


def test_extract_items_from_payload_items_path_missing_key_yields_empty() -> None:
    assert extract_items_from_payload({"entry": []}, "entry[].changes[].value.messages[]") == []
    assert extract_items_from_payload({"other": "shape"}, "entry[].changes[].value.messages[]") == []


def test_parse_timestamp_handles_millisecond_epoch() -> None:
    item = {"id": "1", "timestamp": 1457764197627}
    event = map_generic_item_to_unified_event(
        item, tenant_id="t", slug="viber", field_mapping={"externalId": "id", "timestamp": "timestamp"}
    )
    assert event["timestamp"].startswith("2016-03-12")


def test_map_generic_item_to_unified_event() -> None:
    item = {"id": "42", "updated_at": "2026-07-01T12:00:00Z", "title": "Something happened"}

    event = map_generic_item_to_unified_event(
        item, tenant_id="tenant_demo", slug="my-api", field_mapping=FIELD_MAPPING
    )

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "generic:my-api"
    assert event["externalId"] == "42"
    assert event["eventId"] == "generic-my-api-42"
    assert event["payload"]["text"] == "Something happened"
    assert event["payload"]["identifier"] == "42"


def test_map_generic_item_missing_external_id_raises() -> None:
    try:
        map_generic_item_to_unified_event({}, tenant_id="t", slug="s", field_mapping=FIELD_MAPPING)
    except ValueError:
        pass
    else:  # pragma: no cover - explicit failure branch for readability
        raise AssertionError("Expected ValueError for missing externalId")


def test_map_generic_item_defaults_timestamp_when_unparseable() -> None:
    item = {"id": "1", "updated_at": "not-a-date"}
    event = map_generic_item_to_unified_event(
        item, tenant_id="tenant_demo", slug="my-api", field_mapping=FIELD_MAPPING
    )
    assert event["timestamp"]


def test_connector_fetch_seeded_items() -> None:
    connector = GenericHttpConnector(
        tenant_id="tenant_demo",
        slug="my-api",
        base_url="https://example.invalid/events",
        auth_method="none",
        auth_header_name=None,
        field_mapping=FIELD_MAPPING,
        seeded_items=[{"id": "1", "updated_at": "2026-07-01T12:00:00Z", "title": "hello"}],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["externalId"] == "1"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"


def test_connector_health_degraded_without_base_url_or_seed() -> None:
    connector = GenericHttpConnector(
        tenant_id="tenant_demo",
        slug="my-api",
        base_url=None,
        auth_method="none",
        auth_header_name=None,
        field_mapping=FIELD_MAPPING,
    )
    connector.start()
    assert connector.health().status == "degraded"
