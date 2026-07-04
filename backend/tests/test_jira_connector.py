from app.connectors.jira_connector import JiraConnector, map_jira_issue_to_unified_event


def test_map_jira_issue_to_unified_event() -> None:
    issue = {
        "id": "10001",
        "key": "ENG-42",
        "fields": {
            "summary": "Fix auth regression",
            "updated": "2026-07-01T10:00:00Z",
            "project": {"key": "ENG"},
            "issuetype": {"name": "Bug"},
        },
    }

    event = map_jira_issue_to_unified_event(issue, tenant_id="tenant_demo", base_url="https://org.atlassian.net")

    assert event["tenantId"] == "tenant_demo"
    assert event["sourceType"] == "jira"
    assert event["externalId"] == "10001"
    assert event["payload"]["identifier"] == "ENG-42"
    assert event["payload"]["url"] == "https://org.atlassian.net/browse/ENG-42"


def test_jira_connector_fetch_seeded_events() -> None:
    connector = JiraConnector(
        tenant_id="tenant_demo",
        seeded_issues=[
            {
                "id": "10001",
                "key": "ENG-42",
                "fields": {"summary": "Issue", "project": {"key": "ENG"}, "issuetype": {"name": "Task"}},
            }
        ],
    )
    connector.start()

    events = list(connector.fetch_events())

    assert len(events) == 1
    assert events[0]["eventId"] == "jira-issue-10001"
    assert connector.health().status == "healthy"

    connector.stop()
    assert connector.health().status == "stopped"
