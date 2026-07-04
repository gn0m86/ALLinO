from fastapi.testclient import TestClient

from app.api import ingestion
from app.db import session
from app.main import app


def test_connector_capabilities_endpoint_returns_matrix(tmp_path) -> None:
    session.DB_PATH = tmp_path / "connector_capabilities.db"

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/connectors/capabilities?tenant_id=tenant_demo"
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data

    row = data[0]
    assert "source_type" in row
    assert "available" in row
    assert "configured" in row
    assert "requires_secret" in row
    assert "sync_supported" in row

    source_types = {item["source_type"] for item in data}
    assert {
        "github",
        "gitlab",
        "jira",
        "linear",
        "telegram",
        "slack",
        "discord",
        "zoom",
        "teams",
        "google_calendar",
        "rocketchat",
    }.issubset(source_types)
    by_source = {item["source_type"]: item for item in data}
    assert by_source["zoom"]["sync_supported"] is True
    assert by_source["teams"]["sync_supported"] is True
    assert by_source["google_calendar"]["sync_supported"] is True
    assert by_source["rocketchat"]["sync_supported"] is True


def test_connector_capabilities_reflect_runtime_env_configuration(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "connector_capabilities_env.db"

    monkeypatch.delenv("ALLINO_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_GITLAB_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_JIRA_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_LINEAR_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_SLACK_CHANNEL_ID", raising=False)
    monkeypatch.delenv("ALLINO_DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_DISCORD_CHANNEL_ID", raising=False)
    monkeypatch.delenv("ALLINO_ZOOM_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_TEAMS_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_GOOGLE_CALENDAR_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_ROCKETCHAT_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_ROCKETCHAT_USER_ID", raising=False)
    monkeypatch.delenv("ALLINO_ROCKETCHAT_CHANNEL_ID", raising=False)
    monkeypatch.delenv("ALLINO_ROCKETCHAT_BASE_URL", raising=False)

    monkeypatch.setenv("ALLINO_LINEAR_TOKEN", "linear-token")
    monkeypatch.setenv("ALLINO_SLACK_BOT_TOKEN", "xoxb-token")
    monkeypatch.setenv("ALLINO_SLACK_CHANNEL_ID", "COPS")
    monkeypatch.setenv("ALLINO_DISCORD_BOT_TOKEN", "discord-token")
    monkeypatch.setenv("ALLINO_DISCORD_CHANNEL_ID", "123456")
    monkeypatch.setenv("ALLINO_ZOOM_TOKEN", "zoom-token")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/connectors/capabilities?tenant_id=tenant_demo"
        )

    assert response.status_code == 200
    data = response.json()
    by_source = {item["source_type"]: item for item in data}

    assert by_source["linear"]["configured"] is True
    assert by_source["slack"]["configured"] is True
    assert by_source["discord"]["configured"] is True
    assert by_source["zoom"]["configured"] is True
    assert by_source["zoom"]["sync_supported"] is True
    assert by_source["github"]["configured"] is False
    assert by_source["telegram"]["configured"] is False
    assert by_source["teams"]["configured"] is False
    assert by_source["teams"]["sync_supported"] is True
    assert by_source["google_calendar"]["configured"] is False
    assert by_source["rocketchat"]["configured"] is False


def test_rocketchat_configured_without_channel_id(tmp_path, monkeypatch) -> None:
    """channel_id is optional -- omitting it means "watch every room the user
    belongs to", not "misconfigured". See RocketChatConnector."""
    session.DB_PATH = tmp_path / "connector_capabilities_rocketchat_all_rooms.db"

    monkeypatch.delenv("ALLINO_ROCKETCHAT_CHANNEL_ID", raising=False)
    monkeypatch.setenv("ALLINO_ROCKETCHAT_TOKEN", "rc-token")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_USER_ID", "rc-user")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_BASE_URL", "https://chat.example.com")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/connectors/capabilities?tenant_id=tenant_demo"
        )

    assert response.status_code == 200
    by_source = {item["source_type"]: item for item in response.json()}
    assert by_source["rocketchat"]["configured"] is True


def test_connector_capabilities_support_vault_backed_secret_lookup(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "connector_capabilities_vault.db"

    def fake_has_secret_value(key: str) -> bool:
        return key in {"ALLINO_TEAMS_TOKEN"}

    monkeypatch.setattr(ingestion, "has_secret_value", fake_has_secret_value)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ingestion/connectors/capabilities?tenant_id=tenant_demo"
        )

    assert response.status_code == 200
    by_source = {item["source_type"]: item for item in response.json()}
    assert by_source["teams"]["configured"] is True
    assert by_source["github"]["configured"] is False
