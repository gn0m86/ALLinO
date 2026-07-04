from app.connectors.github_connector import (
    GitHubConnector,
    map_github_notification_to_unified_event,
)


def test_map_github_notification_to_unified_event() -> None:
    notification = {
        "id": "12345",
        "updated_at": "2026-06-25T10:00:00Z",
        "reason": "review_requested",
        "subject": {
            "title": "Review PR #42",
            "type": "PullRequest",
            "url": "https://api.github.com/repos/org/repo/pulls/42",
        },
        "repository": {
            "full_name": "org/repo",
        },
    }

    event = map_github_notification_to_unified_event(notification, tenant_id="tenant_demo")

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "github"
    assert event["externalId"] == "12345"
    assert event["schemaVersion"] == "1.0.0"
    assert "org/repo" in event["payload"]["text"]
    assert "Review PR #42" in event["payload"]["text"]


def test_github_connector_fetch_seeded_events() -> None:
    connector = GitHubConnector(
        tenant_id="tenant_demo",
        seeded_notifications=[{"id": "n1", "subject": {"title": "A"}, "repository": {"full_name": "org/r"}}],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "gh-notification-n1"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"
