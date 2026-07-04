from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db import session
from app.domain.events import UnifiedEvent
from app.main import app
from app.services.normalizer import normalize_event


def _event(payload: dict, source_type: str = "rocketchat", external_id: str = "GENERAL:1") -> UnifiedEvent:
    return UnifiedEvent(
        eventId=f"evt-{external_id}",
        tenantId="tenant_demo",
        sourceType=source_type,
        externalId=external_id,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
        schemaVersion="1.0.0",
    )


def test_normalize_event_includes_valid_attachment() -> None:
    message = normalize_event(_event({"text": "photo", "attachment_ref": "file123", "attachment_type": "image"}))
    assert message.attachment_ref == "file123"
    assert message.attachment_type == "image"


def test_normalize_event_ignores_invalid_attachment_type() -> None:
    message = normalize_event(_event({"text": "doc", "attachment_ref": "file123", "attachment_type": "pdf"}))
    assert message.attachment_ref is None
    assert message.attachment_type is None


def test_normalize_event_without_attachment_fields() -> None:
    message = normalize_event(_event({"text": "just text"}))
    assert message.attachment_ref is None
    assert message.attachment_type is None


def test_normalize_event_includes_generic_file_attachment_with_name() -> None:
    message = normalize_event(
        _event({"text": "", "attachment_ref": "file789", "attachment_type": "file", "attachment_name": "report.pdf"})
    )
    assert message.attachment_ref == "file789"
    assert message.attachment_type == "file"
    assert message.attachment_name == "report.pdf"


def test_normalize_event_includes_attachment_size() -> None:
    message = normalize_event(
        _event(
            {
                "text": "",
                "attachment_ref": "file789",
                "attachment_type": "file",
                "attachment_name": "report.pdf",
                "attachment_size": 174431,
            }
        )
    )
    assert message.attachment_size == 174431


def test_normalize_event_without_attachment_size_defaults_to_none() -> None:
    message = normalize_event(_event({"text": "photo", "attachment_ref": "file123", "attachment_type": "image"}))
    assert message.attachment_size is None


def test_normalize_event_rocketchat_reply_target_is_thread_root_id() -> None:
    message = normalize_event(_event({"text": "hi", "reply_to_message_id": "rootMsg123"}))
    assert message.reply_target == "rootMsg123"


def test_normalize_event_github_reply_target_unaffected_by_rocketchat_field() -> None:
    message = normalize_event(_event({"text": "hi", "reply_to_message_id": "rootMsg123"}, source_type="github"))
    assert message.reply_target is None


def test_normalize_event_includes_valid_channel_kind_and_team() -> None:
    message = normalize_event(
        _event({"text": "hi", "channel_kind": "team", "channel_team": "developer_department"})
    )
    assert message.channel_kind == "team"
    assert message.channel_team == "developer_department"


def test_normalize_event_ignores_invalid_channel_kind() -> None:
    message = normalize_event(_event({"text": "hi", "channel_kind": "not-a-real-kind"}))
    assert message.channel_kind is None


def test_normalize_event_without_channel_kind_fields() -> None:
    message = normalize_event(_event({"text": "just text"}))
    assert message.channel_kind is None
    assert message.channel_team is None


def _seed_event_with_attachment(
    client: TestClient,
    event_id: str,
    attachment_type: str | None = "image",
    attachment_name: str | None = None,
) -> None:
    payload: dict = {"text": "a photo"}
    if attachment_type is not None:
        payload["attachment_ref"] = "fileId123"
        payload["attachment_type"] = attachment_type
        if attachment_name:
            payload["attachment_name"] = attachment_name
    resp = client.post(
        "/api/v1/ingestion/events?tenant_id=tenant_demo",
        json={
            "eventId": event_id,
            "tenantId": "tenant_demo",
            "sourceType": "rocketchat",
            "externalId": event_id,
            "timestamp": "2026-07-03T12:00:00Z",
            "payload": payload,
            "schemaVersion": "1.0.0",
        },
    )
    assert resp.status_code == 200


def test_attachment_endpoint_404_when_message_has_no_attachment(tmp_path) -> None:
    session.DB_PATH = tmp_path / "attach_no_file.db"

    with TestClient(app) as client:
        _seed_event_with_attachment(client, "no-attach-1", attachment_type=None)

        resp = client.get("/api/v1/ingestion/messages/no-attach-1/attachment?tenant_id=tenant_demo")
        assert resp.status_code == 404


def test_attachment_endpoint_404_for_unknown_message(tmp_path) -> None:
    session.DB_PATH = tmp_path / "attach_unknown.db"

    with TestClient(app) as client:
        resp = client.get("/api/v1/ingestion/messages/does-not-exist/attachment?tenant_id=tenant_demo")
        assert resp.status_code == 404


def test_attachment_endpoint_fetches_via_rocketchat_proxy(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "attach_success.db"
    monkeypatch.setenv("ALLINO_ROCKETCHAT_TOKEN", "rc-token")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_USER_ID", "rc-user")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_BASE_URL", "https://chat.example.com")

    def fake_fetch(attachment_ref: str, attachment_type: str):
        assert attachment_ref == "fileId123"
        assert attachment_type == "image"
        return b"fake-image-bytes", "image/jpeg"

    import app.api.attachments as attachments_module

    monkeypatch.setitem(attachments_module._ATTACHMENT_FETCHERS, "rocketchat", fake_fetch)

    with TestClient(app) as client:
        _seed_event_with_attachment(client, "has-attach-1", attachment_type="image")

        resp = client.get("/api/v1/ingestion/messages/has-attach-1/attachment?tenant_id=tenant_demo")
        assert resp.status_code == 200
        assert resp.content == b"fake-image-bytes"
        assert resp.headers["content-type"] == "image/jpeg"
        assert "content-disposition" not in resp.headers


def test_attachment_endpoint_sets_download_filename_for_file_type(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "attach_file_download.db"
    monkeypatch.setenv("ALLINO_ROCKETCHAT_TOKEN", "rc-token")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_USER_ID", "rc-user")
    monkeypatch.setenv("ALLINO_ROCKETCHAT_BASE_URL", "https://chat.example.com")

    def fake_fetch(attachment_ref: str, attachment_type: str):
        return b"fake-file-bytes", "application/octet-stream"

    import app.api.attachments as attachments_module

    monkeypatch.setitem(attachments_module._ATTACHMENT_FETCHERS, "rocketchat", fake_fetch)

    with TestClient(app) as client:
        # A filename with a quote and CRLF -- must not break out of the header's
        # quoted-string or inject an extra header line.
        _seed_event_with_attachment(client, "has-file-1", attachment_type="file", attachment_name='evil".pas\r\nX-Injected: 1')

        resp = client.get("/api/v1/ingestion/messages/has-file-1/attachment?tenant_id=tenant_demo")
        assert resp.status_code == 200
        assert resp.content == b"fake-file-bytes"
        disposition = resp.headers["content-disposition"]
        assert "\r" not in disposition and "\n" not in disposition
        assert disposition == 'attachment; filename="evil_.pas__X-Injected: 1"'


def test_attachment_endpoint_503_when_rocketchat_not_configured(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "attach_not_configured.db"
    monkeypatch.delenv("ALLINO_ROCKETCHAT_TOKEN", raising=False)
    monkeypatch.delenv("ALLINO_ROCKETCHAT_USER_ID", raising=False)
    monkeypatch.delenv("ALLINO_ROCKETCHAT_BASE_URL", raising=False)

    with TestClient(app) as client:
        _seed_event_with_attachment(client, "has-attach-2", attachment_type="image")

        resp = client.get("/api/v1/ingestion/messages/has-attach-2/attachment?tenant_id=tenant_demo")
        assert resp.status_code == 503


def test_attachment_endpoint_is_tenant_scoped(tmp_path) -> None:
    session.DB_PATH = tmp_path / "attach_tenant_scoped.db"

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ingestion/events?tenant_id=tenant_a",
            json={
                "eventId": "cross-tenant-1",
                "tenantId": "tenant_a",
                "sourceType": "rocketchat",
                "externalId": "cross-tenant-1",
                "timestamp": "2026-07-03T12:00:00Z",
                "payload": {"text": "photo", "attachment_ref": "fileId123", "attachment_type": "image"},
                "schemaVersion": "1.0.0",
            },
        )
        assert resp.status_code == 200

        resp = client.get("/api/v1/ingestion/messages/cross-tenant-1/attachment?tenant_id=tenant_b")
        assert resp.status_code == 404
