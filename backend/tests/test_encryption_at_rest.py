from datetime import datetime, UTC

from app.core import crypto
from app.db import session
from app.db.repositories.audit_repo import append_audit, list_audit
from app.db.repositories.connector_runs_repo import append_connector_run, list_connector_runs
from app.db.repositories.connectors_repo import list_connectors, upsert_connector_status
from app.db.repositories.messages_repo import add_if_new, list_messages
from app.domain.events import InboxMessage


def _configure_crypto(monkeypatch) -> None:
    monkeypatch.setattr(crypto, "ALLINO_ENCRYPTION_AT_REST_ENABLED", True)
    monkeypatch.setattr(crypto, "ALLINO_ENCRYPTION_KEY", "unit-test-encryption-key")
    monkeypatch.setattr(crypto, "_CACHED_FERNET", None)


def test_audit_metadata_encrypted_at_rest(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "enc_audit.db"
    session.init_db()
    _configure_crypto(monkeypatch)

    append_audit(tenant_id="tenant_a", action="ingest", metadata={"token": "secret-value"})

    with session.get_connection() as conn:
        row = conn.execute("SELECT metadata FROM audit_logs LIMIT 1").fetchone()
        raw_metadata = row["metadata"]

    assert raw_metadata.startswith("enc:v1:")
    assert "secret-value" not in raw_metadata

    records = list_audit("tenant_a", limit=10)
    assert '"token": "secret-value"' in records[0]["metadata"]


def test_message_preview_encrypted_at_rest(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "enc_messages.db"
    session.init_db()
    _configure_crypto(monkeypatch)

    message = InboxMessage(
        event_id="evt-1",
        tenant_id="tenant_a",
        source="github",
        external_id="ext-1",
        timestamp=datetime.now(UTC),
        preview="super-secret-preview",
        thread_key="thread-1",
        priority="normal",
    )

    assert add_if_new("dedup-1", message) is True

    with session.get_connection() as conn:
        row = conn.execute("SELECT preview FROM messages LIMIT 1").fetchone()
        raw_preview = row["preview"]

    assert raw_preview.startswith("enc:v1:")
    assert "super-secret-preview" not in raw_preview

    records = list_messages("tenant_a", limit=10)
    assert records[0].preview == "super-secret-preview"


def test_connector_errors_encrypted_at_rest(monkeypatch, tmp_path) -> None:
    session.DB_PATH = tmp_path / "enc_connectors.db"
    session.init_db()
    _configure_crypto(monkeypatch)

    upsert_connector_status(
        tenant_id="tenant_a",
        source_type="github",
        status="error",
        last_error="provider token leaked",
    )
    append_connector_run(
        tenant_id="tenant_a",
        source_type="github",
        status="error",
        synced_at=datetime.now(UTC).isoformat(),
        error="provider token leaked",
    )

    with session.get_connection() as conn:
        row_connector = conn.execute("SELECT last_error FROM connectors LIMIT 1").fetchone()
        row_run = conn.execute("SELECT error FROM connector_runs LIMIT 1").fetchone()

    assert row_connector["last_error"].startswith("enc:v1:")
    assert row_run["error"].startswith("enc:v1:")
    assert "provider token leaked" not in row_connector["last_error"]
    assert "provider token leaked" not in row_run["error"]

    connectors = list_connectors("tenant_a")
    runs = list_connector_runs(tenant_id="tenant_a", limit=10)
    assert connectors[0]["last_error"] == "provider token leaked"
    assert runs[0]["error"] == "provider token leaked"
