from app.connectors import MockConnector, RetryPolicy


def test_mock_connector_lifecycle_and_fetch() -> None:
    connector = MockConnector(
        source="mock-test",
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
        events=[{"eventId": "e1"}, {"eventId": "e2"}],
    )

    assert connector.health().status == "stopped"

    connector.start()
    assert connector.health().status == "healthy"

    events = list(connector.fetch_events())
    assert len(events) == 2

    tail_events = list(connector.fetch_events(cursor="1"))
    assert [item["eventId"] for item in tail_events] == ["e2"]

    connector.stop()
    assert connector.health().status == "stopped"
