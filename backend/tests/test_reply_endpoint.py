from fastapi.testclient import TestClient

from app.api import replies as replies_module
from app.db import session
from app.main import app


def _seed_telegram_message(client: TestClient, tenant_id: str = "tenant_demo") -> str:
    update = {
        "update_id": 1,
        "message": {
            "message_id": 55,
            "chat": {"id": 42, "title": "Ops"},
            "date": 1780000000,
            "from": {"username": "alice"},
            "text": "server is down",
        },
    }
    resp = client.post(
        f"/api/v1/ingestion/connectors/telegram/sync?tenant_id={tenant_id}",
        json={"seeded_updates": [update]},
    )
    assert resp.status_code == 200
    return "tg-update-1"


def test_reply_to_unknown_message_returns_404(tmp_path) -> None:
    session.DB_PATH = tmp_path / "reply_unknown.db"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/messages/does-not-exist/reply?tenant_id=tenant_demo",
            json={"text": "hi"},
        )
        assert resp.status_code == 404


def test_reply_to_unsupported_source_returns_400(tmp_path) -> None:
    session.DB_PATH = tmp_path / "reply_unsupported.db"

    with TestClient(app) as client:
        seed_resp = client.post(
            "/api/v1/ingestion/events?tenant_id=tenant_demo",
            json={
                "eventId": "evt-1",
                "tenantId": "tenant_demo",
                "sourceType": "zoom",
                "externalId": "zoom-1",
                "timestamp": "2026-07-01T12:00:00Z",
                "payload": {"text": "Meeting scheduled"},
                "schemaVersion": "1.0.0",
            },
        )
        assert seed_resp.status_code == 200

        resp = client.post(
            "/api/v1/ingestion/messages/evt-1/reply?tenant_id=tenant_demo",
            json={"text": "hi"},
        )
        assert resp.status_code == 400


def test_reply_without_configured_token_returns_503(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_no_token.db"
    monkeypatch.delenv("ALLINO_TELEGRAM_BOT_TOKEN", raising=False)

    with TestClient(app) as client:
        event_id = _seed_telegram_message(client)

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 503


def test_reply_success_records_audit_and_history(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_success.db"
    monkeypatch.setenv("ALLINO_TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setitem(
        replies_module._REPLY_SENDERS,
        "telegram",
        lambda **kwargs: {"ok": True, "result": {"message_id": 1}},
    )

    with TestClient(app) as client:
        event_id = _seed_telegram_message(client)

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"

        replies_resp = client.get("/api/v1/ingestion/replies?tenant_id=tenant_demo")
        assert replies_resp.status_code == 200
        history = replies_resp.json()
        assert len(history) == 1
        assert history[0]["status"] == "sent"
        assert history[0]["text"] == "on it"

        audit_resp = client.get("/api/v1/ingestion/audit?tenant_id=tenant_demo")
        actions = [row["action"] for row in audit_resp.json()]
        assert "message.reply.sent" in actions


def test_reply_delivery_failure_records_error(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_failure.db"
    monkeypatch.setenv("ALLINO_TELEGRAM_BOT_TOKEN", "tok123")

    def _boom(**kwargs):
        raise RuntimeError("Telegram API error: chat not found")

    monkeypatch.setitem(replies_module._REPLY_SENDERS, "telegram", _boom)

    with TestClient(app) as client:
        event_id = _seed_telegram_message(client)

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 502

        replies_resp = client.get("/api/v1/ingestion/replies?tenant_id=tenant_demo")
        history = replies_resp.json()
        assert history[0]["status"] == "failed"
        assert "chat not found" in history[0]["error"]


def _seed_rocketchat_message(client: TestClient, tenant_id: str = "tenant_demo") -> str:
    message = {
        "_id": "3001",
        "ts": "2026-07-02T12:10:00Z",
        "msg": "deploy finished",
        "rid": "GENERAL",
        "u": {"username": "ops-bot"},
    }
    resp = client.post(
        f"/api/v1/ingestion/connectors/rocketchat/sync?tenant_id={tenant_id}",
        json={"channel_id": "GENERAL", "seeded_messages": [message]},
    )
    assert resp.status_code == 200
    return "rocketchat-message-GENERAL:3001"


def test_reply_rocketchat_missing_extra_config_returns_503(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_rocketchat_no_extra_config.db"
    monkeypatch.setenv("ALLINO_ROCKETCHAT_TOKEN", "rc-token")
    monkeypatch.delenv("ALLINO_ROCKETCHAT_USER_ID", raising=False)
    monkeypatch.delenv("ALLINO_ROCKETCHAT_BASE_URL", raising=False)

    with TestClient(app) as client:
        event_id = _seed_rocketchat_message(client)

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 503


def test_reply_rocketchat_success_records_audit_and_history(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_rocketchat_success.db"
    monkeypatch.setenv("ALLINO_ROCKETCHAT_TOKEN", "rc-token")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_USER_ID", "rc-user")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_BASE_URL", "https://chat.example.com")
    monkeypatch.setitem(
        replies_module._REPLY_SENDERS,
        "rocketchat",
        lambda **kwargs: {"success": True, "message": {"_id": "3002"}},
    )

    with TestClient(app) as client:
        event_id = _seed_rocketchat_message(client)

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"

        replies_resp = client.get("/api/v1/ingestion/replies?tenant_id=tenant_demo")
        history = replies_resp.json()
        assert len(history) == 1
        assert history[0]["status"] == "sent"


def _seed_github_message(
    client: TestClient,
    tenant_id: str = "tenant_demo",
    subject_url: str = "https://api.github.com/repos/owner/repo/issues/42",
) -> str:
    notification = {
        "id": "555",
        "subject": {"title": "Fix bug", "type": "Issue", "url": subject_url},
        "repository": {"full_name": "owner/repo"},
        "reason": "mention",
        "updated_at": "2026-07-02T12:00:00Z",
    }
    resp = client.post(
        f"/api/v1/ingestion/connectors/github/sync?tenant_id={tenant_id}",
        json={"seeded_notifications": [notification]},
    )
    assert resp.status_code == 200
    return "gh-notification-555"


def _seed_gitlab_message(
    client: TestClient,
    tenant_id: str = "tenant_demo",
    target_url: str = "https://gitlab.com/group/project/-/issues/10",
) -> str:
    notification = {
        "id": "777",
        "target_type": "Issue",
        "target_url": target_url,
        "project": {"path_with_namespace": "group/project"},
        "action_name": "opened",
        "created_at": "2026-07-02T12:00:00Z",
    }
    resp = client.post(
        f"/api/v1/ingestion/connectors/gitlab/sync?tenant_id={tenant_id}",
        json={"seeded_notifications": [notification]},
    )
    assert resp.status_code == 200
    return "gl-notification-777"


def _seed_jira_message(client: TestClient, tenant_id: str = "tenant_demo") -> str:
    issue = {
        "id": "10042",
        "key": "PROJ-1",
        "fields": {
            "summary": "Fix bug",
            "project": {"key": "PROJ"},
            "issuetype": {"name": "Bug"},
            "updated": "2026-07-02T12:00:00Z",
        },
    }
    resp = client.post(
        f"/api/v1/ingestion/connectors/jira/sync?tenant_id={tenant_id}",
        json={"seeded_issues": [issue]},
    )
    assert resp.status_code == 200
    return "jira-issue-10042"


def _seed_linear_message(client: TestClient, tenant_id: str = "tenant_demo") -> str:
    node = {
        "id": "issue-uuid-1",
        "identifier": "ENG-1",
        "title": "Fix bug",
        "url": "https://linear.app/team/issue/ENG-1",
        "createdAt": "2026-07-02T12:00:00Z",
        "state": {"name": "Todo"},
        "team": {"key": "ENG"},
    }
    resp = client.post(
        f"/api/v1/ingestion/connectors/linear/sync?tenant_id={tenant_id}",
        json={"seeded_events": [node]},
    )
    assert resp.status_code == 200
    return "linear-issue-issue-uuid-1"


def test_reply_github_missing_reply_target_returns_400(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_github_missing_target.db"
    monkeypatch.setenv("ALLINO_GITHUB_TOKEN", "gh-token")

    with TestClient(app) as client:
        event_id = _seed_github_message(client, subject_url="")

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 400


def test_reply_github_success_records_audit_and_history(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_github_success.db"
    monkeypatch.setenv("ALLINO_GITHUB_TOKEN", "gh-token")
    monkeypatch.setitem(
        replies_module._REPLY_SENDERS,
        "github",
        lambda **kwargs: {"id": 1},
    )

    with TestClient(app) as client:
        event_id = _seed_github_message(client)

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"

        replies_resp = client.get("/api/v1/ingestion/replies?tenant_id=tenant_demo")
        history = replies_resp.json()
        assert len(history) == 1
        assert history[0]["status"] == "sent"


def test_reply_gitlab_missing_reply_target_returns_400(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_gitlab_missing_target.db"
    monkeypatch.setenv("ALLINO_GITLAB_TOKEN", "gl-token")

    with TestClient(app) as client:
        event_id = _seed_gitlab_message(client, target_url="")

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 400


def test_reply_gitlab_success_records_audit_and_history(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_gitlab_success.db"
    monkeypatch.setenv("ALLINO_GITLAB_TOKEN", "gl-token")
    monkeypatch.setitem(
        replies_module._REPLY_SENDERS,
        "gitlab",
        lambda **kwargs: {"id": 1},
    )

    with TestClient(app) as client:
        event_id = _seed_gitlab_message(client)

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"


def test_reply_jira_success_records_audit_and_history(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_jira_success.db"
    monkeypatch.setenv("ALLINO_JIRA_TOKEN", "jira-token")
    monkeypatch.setitem(
        replies_module._REPLY_SENDERS,
        "jira",
        lambda **kwargs: {"id": "10001"},
    )

    with TestClient(app) as client:
        event_id = _seed_jira_message(client)

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"


def test_reply_linear_success_records_audit_and_history(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_linear_success.db"
    monkeypatch.setenv("ALLINO_LINEAR_TOKEN", "lin-token")
    monkeypatch.setitem(
        replies_module._REPLY_SENDERS,
        "linear",
        lambda **kwargs: {"data": {"commentCreate": {"success": True}}},
    )

    with TestClient(app) as client:
        event_id = _seed_linear_message(client)

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_demo",
            json={"text": "on it"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"


def test_reply_is_tenant_scoped(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "reply_tenant_scope.db"
    monkeypatch.setenv("ALLINO_TELEGRAM_BOT_TOKEN", "tok123")

    with TestClient(app) as client:
        event_id = _seed_telegram_message(client, tenant_id="tenant_a")

        resp = client.post(
            f"/api/v1/ingestion/messages/{event_id}/reply?tenant_id=tenant_b",
            json={"text": "on it"},
        )
        assert resp.status_code == 404
