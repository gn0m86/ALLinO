import httpx
import pytest

from app.connectors.discord_connector import send_discord_reply
from app.connectors.github_connector import send_github_reply
from app.connectors.gitlab_connector import send_gitlab_reply
from app.connectors.jira_connector import send_jira_reply
from app.connectors.linear_connector import send_linear_reply
from app.connectors.rocketchat_connector import send_rocketchat_reply
from app.connectors.slack_connector import send_slack_reply
from app.connectors.telegram_connector import send_telegram_reply


class _FakeResponse:
    def __init__(self, json_body: dict, status_code: int = 200) -> None:
        self._json_body = json_body
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.invalid")
            raise httpx.HTTPStatusError("error", request=request, response=httpx.Response(self.status_code))

    def json(self) -> dict:
        return self._json_body


def test_send_telegram_reply_builds_expected_request(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse({"ok": True, "result": {"message_id": 999}})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = send_telegram_reply(token="tok123", external_id="42:100", text="hello")

    assert "bottok123" in captured["url"]
    assert captured["json"]["chat_id"] == "42"
    assert captured["json"]["reply_to_message_id"] == 100
    assert captured["json"]["text"] == "hello"
    assert result["ok"] is True


def test_send_telegram_reply_without_message_id() -> None:
    with pytest.raises(ValueError):
        send_telegram_reply(token="tok123", external_id="", text="hello")


def test_send_telegram_reply_raises_on_api_error(monkeypatch) -> None:
    def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"ok": False, "description": "chat not found"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with pytest.raises(RuntimeError, match="chat not found"):
        send_telegram_reply(token="tok123", external_id="42:100", text="hello")


def test_send_slack_reply_builds_expected_request(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse({"ok": True, "ts": "123.456"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = send_slack_reply(token="tok123", external_id="C123:1780000100.000200", text="hello")

    assert captured["url"] == "https://slack.com/api/chat.postMessage"
    assert captured["json"]["channel"] == "C123"
    assert captured["json"]["thread_ts"] == "1780000100.000200"
    assert captured["headers"]["Authorization"] == "Bearer tok123"
    assert result["ok"] is True


def test_send_slack_reply_without_channel_raises() -> None:
    with pytest.raises(ValueError):
        send_slack_reply(token="tok123", external_id="", text="hello")


def test_send_slack_reply_raises_on_api_error(monkeypatch) -> None:
    def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"ok": False, "error": "channel_not_found"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with pytest.raises(RuntimeError, match="channel_not_found"):
        send_slack_reply(token="tok123", external_id="C123:1780000100.000200", text="hello")


def test_send_discord_reply_builds_expected_request(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse({"id": "2002", "content": "hello"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = send_discord_reply(token="bottok", external_id="987:2001", text="hello")

    assert captured["url"] == "https://discord.com/api/v10/channels/987/messages"
    assert captured["json"]["content"] == "hello"
    assert captured["json"]["message_reference"] == {"message_id": "2001"}
    assert captured["headers"]["Authorization"] == "Bot bottok"
    assert result["id"] == "2002"


def test_send_discord_reply_without_channel_raises() -> None:
    with pytest.raises(ValueError):
        send_discord_reply(token="bottok", external_id="", text="hello")


def test_send_discord_reply_raises_on_http_error(monkeypatch) -> None:
    def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"message": "Unauthorized"}, status_code=401)

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with pytest.raises(httpx.HTTPStatusError):
        send_discord_reply(token="bad-token", external_id="987:2001", text="hello")


def test_send_rocketchat_reply_builds_expected_request(monkeypatch) -> None:
    monkeypatch.setenv("ALLINO_ROCKETCHAT_USER_ID", "rc-user")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_BASE_URL", "https://chat.example.com")
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse({"success": True, "message": {"_id": "3002"}})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = send_rocketchat_reply(token="rc-token", external_id="GENERAL:3001", text="hello")

    assert captured["url"] == "https://chat.example.com/api/v1/chat.postMessage"
    assert captured["json"]["roomId"] == "GENERAL"
    assert captured["json"]["text"] == "hello"
    assert captured["json"]["tmid"] == "3001"
    assert captured["headers"]["X-Auth-Token"] == "rc-token"
    assert captured["headers"]["X-User-Id"] == "rc-user"
    assert result["success"] is True


def test_send_rocketchat_reply_without_message_id_omits_tmid(monkeypatch) -> None:
    monkeypatch.setenv("ALLINO_ROCKETCHAT_USER_ID", "rc-user")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_BASE_URL", "https://chat.example.com")
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["json"] = json
        return _FakeResponse({"success": True, "message": {"_id": "3002"}})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    send_rocketchat_reply(token="rc-token", external_id="GENERAL", text="hello")

    assert captured["json"]["roomId"] == "GENERAL"
    assert "tmid" not in captured["json"]


def test_send_rocketchat_reply_without_channel_raises() -> None:
    with pytest.raises(ValueError):
        send_rocketchat_reply(token="rc-token", external_id="", text="hello")


def test_send_rocketchat_reply_without_user_id_raises(monkeypatch) -> None:
    monkeypatch.delenv("ALLINO_ROCKETCHAT_USER_ID", raising=False)
    monkeypatch.setenv("ALLINO_ROCKETCHAT_BASE_URL", "https://chat.example.com")

    with pytest.raises(RuntimeError):
        send_rocketchat_reply(token="rc-token", external_id="GENERAL:3001", text="hello")


def test_send_rocketchat_reply_raises_on_api_error(monkeypatch) -> None:
    monkeypatch.setenv("ALLINO_ROCKETCHAT_USER_ID", "rc-user")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_BASE_URL", "https://chat.example.com")

    def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"success": False, "error": "room-not-found"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with pytest.raises(RuntimeError, match="room-not-found"):
        send_rocketchat_reply(token="rc-token", external_id="GENERAL:3001", text="hello")


def test_send_github_reply_builds_expected_request(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse({"id": 999, "body": "hello"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = send_github_reply(
        token="gh-token",
        external_id="1234567",
        text="hello",
        reply_target="https://api.github.com/repos/owner/repo/issues/42",
    )

    assert captured["url"] == "https://api.github.com/repos/owner/repo/issues/42/comments"
    assert captured["json"]["body"] == "hello"
    assert captured["headers"]["Authorization"] == "Bearer gh-token"
    assert result["id"] == 999


def test_send_github_reply_without_reply_target_raises() -> None:
    with pytest.raises(ValueError):
        send_github_reply(token="gh-token", external_id="1234567", text="hello")


def test_send_github_reply_raises_on_http_error(monkeypatch) -> None:
    def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"message": "Not Found"}, status_code=404)

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with pytest.raises(httpx.HTTPStatusError):
        send_github_reply(
            token="gh-token",
            external_id="1234567",
            text="hello",
            reply_target="https://api.github.com/repos/owner/repo/issues/42",
        )


def test_send_gitlab_reply_builds_expected_request_for_issue(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse({"id": 55, "body": "hello"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = send_gitlab_reply(
        token="gl-token",
        external_id="203",
        text="hello",
        reply_target="https://gitlab.com/group/project/-/issues/10",
    )

    assert captured["url"] == "https://gitlab.com/api/v4/projects/group%2Fproject/issues/10/notes"
    assert captured["json"]["body"] == "hello"
    assert captured["headers"]["PRIVATE-TOKEN"] == "gl-token"
    assert result["id"] == 55


def test_send_gitlab_reply_builds_expected_request_for_merge_request(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        return _FakeResponse({"id": 56})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    send_gitlab_reply(
        token="gl-token",
        external_id="204",
        text="hello",
        reply_target="https://gitlab.example.com/group/subgroup/project/-/merge_requests/5#note_123",
        base_url="https://gitlab.example.com",
    )

    assert captured["url"] == (
        "https://gitlab.example.com/api/v4/projects/group%2Fsubgroup%2Fproject/merge_requests/5/notes"
    )


def test_send_gitlab_reply_without_reply_target_raises() -> None:
    with pytest.raises(ValueError):
        send_gitlab_reply(token="gl-token", external_id="203", text="hello")


def test_send_gitlab_reply_unrecognized_target_url_raises() -> None:
    with pytest.raises(ValueError):
        send_gitlab_reply(
            token="gl-token",
            external_id="203",
            text="hello",
            reply_target="https://gitlab.com/group/project/some/other/path",
        )


def test_send_jira_reply_builds_expected_request(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse({"id": "10001"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = send_jira_reply(
        token="jira-token",
        external_id="10042",
        text="hello",
        base_url="https://example.atlassian.net",
    )

    assert captured["url"] == "https://example.atlassian.net/rest/api/3/issue/10042/comment"
    assert captured["json"]["body"]["content"][0]["content"][0]["text"] == "hello"
    assert captured["headers"]["Authorization"] == "Bearer jira-token"
    assert result["id"] == "10001"


def test_send_jira_reply_without_external_id_raises() -> None:
    with pytest.raises(ValueError):
        send_jira_reply(token="jira-token", external_id="", text="hello")


def test_send_linear_reply_builds_expected_request(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse({"data": {"commentCreate": {"success": True}}})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = send_linear_reply(token="lin-token", external_id="issue-uuid-1", text="hello")

    assert captured["url"] == "https://api.linear.app/graphql"
    assert captured["json"]["variables"]["issueId"] == "issue-uuid-1"
    assert captured["json"]["variables"]["body"] == "hello"
    assert captured["headers"]["Authorization"] == "lin-token"
    assert result["data"]["commentCreate"]["success"] is True


def test_send_linear_reply_without_external_id_raises() -> None:
    with pytest.raises(ValueError):
        send_linear_reply(token="lin-token", external_id="", text="hello")


def test_send_linear_reply_raises_when_not_successful(monkeypatch) -> None:
    def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"data": {"commentCreate": {"success": False}}})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with pytest.raises(RuntimeError):
        send_linear_reply(token="lin-token", external_id="issue-uuid-1", text="hello")


def test_send_linear_reply_raises_on_graphql_errors(monkeypatch) -> None:
    def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"errors": [{"message": "not found"}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with pytest.raises(RuntimeError, match="not found"):
        send_linear_reply(token="lin-token", external_id="issue-uuid-1", text="hello")
