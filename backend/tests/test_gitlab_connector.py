from app.connectors.gitlab_connector import (
    GitLabConnector,
    map_gitlab_notification_to_unified_event,
)


def test_map_gitlab_notification_to_unified_event() -> None:
    notification = {
        "id": 777,
        "created_at": "2026-06-25T10:00:00Z",
        "action_name": "mentioned",
        "target_title": "Fix build",
        "target_type": "MergeRequest",
        "target_url": "https://gitlab.com/org/repo/-/merge_requests/1",
        "project": {"path_with_namespace": "org/repo"},
    }

    event = map_gitlab_notification_to_unified_event(notification, tenant_id="tenant_demo")

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "gitlab"
    assert event["externalId"] == "777"
    assert event["schemaVersion"] == "1.0.0"
    assert "org/repo" in event["payload"]["text"]
    assert "Fix build" in event["payload"]["text"]


def test_gitlab_connector_fetch_seeded_events() -> None:
    connector = GitLabConnector(
        tenant_id="tenant_demo",
        seeded_notifications=[
            {
                "id": 1,
                "target_title": "Pipeline failed",
                "project": {"path_with_namespace": "org/repo"},
            }
        ],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "gl-notification-1"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"
