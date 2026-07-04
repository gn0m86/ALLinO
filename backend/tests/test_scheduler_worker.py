from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import session
from app.main import app
from app.workers import scheduler_worker


def _create_generic_connector(client: TestClient, *, name: str, poll_interval_seconds=60, base_url="https://example.invalid/events"):
    resp = client.post(
        "/api/v1/ingestion/connectors/generic?tenant_id=tenant_demo",
        json={
            "name": name,
            "base_url": base_url,
            "auth_method": "none",
            "poll_interval_seconds": poll_interval_seconds,
            "field_mapping": {"externalId": "id", "timestamp": "updated_at", "preview": "title"},
            "webhook_enabled": False,
        },
    )
    assert resp.status_code == 200
    return resp.json()


def test_is_due_true_when_never_synced(tmp_path) -> None:
    session.DB_PATH = tmp_path / "scheduler_never_synced.db"

    with TestClient(app):
        config = {"tenant_id": "tenant_demo", "slug": "brand-new", "poll_interval_seconds": 60}
        assert scheduler_worker._is_due(config, now=datetime.now(timezone.utc)) is True


def test_is_due_false_without_poll_interval(tmp_path) -> None:
    session.DB_PATH = tmp_path / "scheduler_no_interval.db"

    with TestClient(app):
        config = {"tenant_id": "tenant_demo", "slug": "no-interval", "poll_interval_seconds": None}
        assert scheduler_worker._is_due(config, now=datetime.now(timezone.utc)) is False


def test_is_due_respects_recent_last_synced_at(tmp_path) -> None:
    session.DB_PATH = tmp_path / "scheduler_recent.db"

    with TestClient(app):
        from app.db.repositories.connectors_repo import upsert_connector_status

        upsert_connector_status(
            tenant_id="tenant_demo",
            source_type="generic:recent",
            status="healthy",
            last_synced_at=datetime.now(timezone.utc).isoformat(),
        )
        config = {"tenant_id": "tenant_demo", "slug": "recent", "poll_interval_seconds": 3600}
        assert scheduler_worker._is_due(config, now=datetime.now(timezone.utc)) is False


def test_is_due_true_once_interval_elapsed(tmp_path) -> None:
    session.DB_PATH = tmp_path / "scheduler_stale.db"

    with TestClient(app):
        from app.db.repositories.connectors_repo import upsert_connector_status

        stale_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        upsert_connector_status(
            tenant_id="tenant_demo",
            source_type="generic:stale",
            status="healthy",
            last_synced_at=stale_time.isoformat(),
        )
        config = {"tenant_id": "tenant_demo", "slug": "stale", "poll_interval_seconds": 60}
        assert scheduler_worker._is_due(config, now=datetime.now(timezone.utc)) is True


def test_run_scheduler_tick_syncs_only_due_connectors(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick.db"

    with TestClient(app) as client:
        due = _create_generic_connector(client, name="Due Source", poll_interval_seconds=60)
        _create_generic_connector(client, name="No Interval Source", poll_interval_seconds=None)

        calls = []

        def fake_sync(*, config, tenant_id, retry_policy=None, seeded_items=None):
            calls.append(config["slug"])
            return {"tenant_id": tenant_id, "processed": 0, "inserted": 0, "duplicates": 0, "rejected": 0}

        monkeypatch.setattr(scheduler_worker, "sync_generic_connector", fake_sync)

        results = scheduler_worker.run_scheduler_tick()

        assert calls == [due["slug"]]
        assert len(results) == 1
        assert results[0]["ok"] is True
        assert results[0]["slug"] == due["slug"]


def test_run_scheduler_tick_records_failure_without_raising(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_failure.db"

    with TestClient(app) as client:
        config = _create_generic_connector(client, name="Flaky Source", poll_interval_seconds=60)

        from app.services.connector_sync import GenericConnectorSyncError

        def fake_sync(*, config, tenant_id, retry_policy=None, seeded_items=None):
            raise GenericConnectorSyncError(config["slug"], RuntimeError("boom"))

        monkeypatch.setattr(scheduler_worker, "sync_generic_connector", fake_sync)

        results = scheduler_worker.run_scheduler_tick()

        assert len(results) == 1
        assert results[0]["ok"] is False
        assert results[0]["slug"] == config["slug"]
        assert "boom" not in results[0]["error"]  # message is the wrapper text, not the raw cause


def test_run_scheduler_tick_skips_connector_without_base_url(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_no_base_url.db"

    with TestClient(app) as client:
        _create_generic_connector(client, name="No URL Source", poll_interval_seconds=60, base_url=None)

        calls = []
        monkeypatch.setattr(
            scheduler_worker,
            "sync_generic_connector",
            lambda **kwargs: calls.append(1),
        )

        results = scheduler_worker.run_scheduler_tick()

        assert calls == []
        assert results == []


def test_check_worker_health_ok(tmp_path) -> None:
    session.DB_PATH = tmp_path / "scheduler_health.db"

    with TestClient(app):
        ok, message = scheduler_worker.check_worker_health()
        assert ok is True
        assert message == "ok"


def test_google_calendar_not_due_when_disabled(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_gcal_disabled.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_ENABLED", False)
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID", "tenant_demo")

    with TestClient(app):
        assert scheduler_worker._is_google_calendar_due(now=datetime.now(timezone.utc)) is False


def test_google_calendar_not_due_without_tenant_id(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_gcal_no_tenant.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID", None)

    with TestClient(app):
        assert scheduler_worker._is_google_calendar_due(now=datetime.now(timezone.utc)) is False


def test_google_calendar_due_when_never_synced(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_gcal_never_synced.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID", "tenant_demo")

    with TestClient(app):
        assert scheduler_worker._is_google_calendar_due(now=datetime.now(timezone.utc)) is True


def test_google_calendar_not_due_when_recently_synced(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_gcal_recent.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID", "tenant_demo")
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_INTERVAL_SECONDS", 3600)

    with TestClient(app):
        from app.db.repositories.connectors_repo import upsert_connector_status

        upsert_connector_status(
            tenant_id="tenant_demo",
            source_type="google_calendar",
            status="healthy",
            last_synced_at=datetime.now(timezone.utc).isoformat(),
        )
        assert scheduler_worker._is_google_calendar_due(now=datetime.now(timezone.utc)) is False


def test_google_calendar_due_once_interval_elapsed(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_gcal_stale.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID", "tenant_demo")
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_INTERVAL_SECONDS", 60)

    with TestClient(app):
        from app.db.repositories.connectors_repo import upsert_connector_status

        stale_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        upsert_connector_status(
            tenant_id="tenant_demo",
            source_type="google_calendar",
            status="healthy",
            last_synced_at=stale_time.isoformat(),
        )
        assert scheduler_worker._is_google_calendar_due(now=datetime.now(timezone.utc)) is True


def test_run_scheduler_tick_syncs_google_calendar_when_due(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_gcal.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID", "tenant_demo")
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_CALENDAR_ID", "primary")

    calls = []

    def fake_sync(*, tenant_id, calendar_id=None, token=None, client_id=None, client_secret=None, refresh_token=None, retry_policy=None, seeded_events=None):
        calls.append((tenant_id, calendar_id))
        return {"tenant_id": tenant_id, "processed": 0, "inserted": 0, "duplicates": 0, "rejected": 0}

    monkeypatch.setattr(scheduler_worker, "sync_google_calendar_connector", fake_sync)

    with TestClient(app):
        results = scheduler_worker.run_scheduler_tick()

    assert calls == [("tenant_demo", "primary")]
    assert len(results) == 1
    assert results[0]["ok"] is True
    assert results[0]["slug"] == "google_calendar"


def test_run_scheduler_tick_records_google_calendar_failure_without_raising(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_gcal_failure.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID", "tenant_demo")

    from app.services.connector_sync import GoogleCalendarSyncError

    def fake_sync(*, tenant_id, calendar_id=None, token=None, client_id=None, client_secret=None, refresh_token=None, retry_policy=None, seeded_events=None):
        raise GoogleCalendarSyncError(tenant_id, RuntimeError("boom"))

    monkeypatch.setattr(scheduler_worker, "sync_google_calendar_connector", fake_sync)

    with TestClient(app):
        results = scheduler_worker.run_scheduler_tick()

    assert len(results) == 1
    assert results[0]["ok"] is False
    assert results[0]["slug"] == "google_calendar"
    assert "boom" not in results[0]["error"]


def test_builtin_connector_not_due_when_disabled(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_builtin_disabled.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED", False)
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID", "tenant_demo")
    monkeypatch.setattr(scheduler_worker, "has_secret_value", lambda key: True)

    calls = []
    monkeypatch.setattr(scheduler_worker, "sync_builtin_connector", lambda **kwargs: calls.append(1))

    with TestClient(app):
        results = scheduler_worker.run_scheduler_tick()

    assert calls == []
    assert results == []


def test_builtin_connector_skipped_without_secret_configured(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_builtin_no_secret.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID", "tenant_demo")
    monkeypatch.setattr(scheduler_worker, "has_secret_value", lambda key: False)

    calls = []
    monkeypatch.setattr(scheduler_worker, "sync_builtin_connector", lambda **kwargs: calls.append(1))

    with TestClient(app):
        results = scheduler_worker.run_scheduler_tick()

    assert calls == []
    assert results == []


def test_builtin_connector_due_when_never_synced(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_builtin_never_synced.db"

    with TestClient(app):
        assert scheduler_worker._is_builtin_connector_due(
            "github", "tenant_demo", now=datetime.now(timezone.utc)
        ) is True


def test_builtin_connector_not_due_when_recently_synced(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_builtin_recent.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_INTERVAL_SECONDS", 3600)

    with TestClient(app):
        from app.db.repositories.connectors_repo import upsert_connector_status

        upsert_connector_status(
            tenant_id="tenant_demo",
            source_type="github",
            status="healthy",
            last_synced_at=datetime.now(timezone.utc).isoformat(),
        )
        assert scheduler_worker._is_builtin_connector_due(
            "github", "tenant_demo", now=datetime.now(timezone.utc)
        ) is False


def test_builtin_connector_due_once_interval_elapsed(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_builtin_stale.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_INTERVAL_SECONDS", 60)

    with TestClient(app):
        from app.db.repositories.connectors_repo import upsert_connector_status

        stale_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        upsert_connector_status(
            tenant_id="tenant_demo",
            source_type="github",
            status="healthy",
            last_synced_at=stale_time.isoformat(),
        )
        assert scheduler_worker._is_builtin_connector_due(
            "github", "tenant_demo", now=datetime.now(timezone.utc)
        ) is True


def test_run_scheduler_tick_syncs_only_configured_and_due_builtin_connectors(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_builtin.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID", "tenant_demo")
    monkeypatch.setattr(scheduler_worker, "has_secret_value", lambda key: key == "ALLINO_GITHUB_TOKEN")

    calls = []

    def fake_sync(*, connector, source, tenant_id, action_prefix):
        calls.append(source)
        return {"tenant_id": tenant_id, "processed": 0, "inserted": 0, "duplicates": 0, "rejected": 0}

    monkeypatch.setattr(scheduler_worker, "sync_builtin_connector", fake_sync)

    with TestClient(app):
        results = scheduler_worker.run_scheduler_tick()

    assert calls == ["github"]
    assert len(results) == 1
    assert results[0]["ok"] is True
    assert results[0]["slug"] == "github"


def test_run_scheduler_tick_records_builtin_connector_failure_without_raising(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_builtin_failure.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID", "tenant_demo")
    monkeypatch.setattr(scheduler_worker, "has_secret_value", lambda key: key == "ALLINO_GITHUB_TOKEN")

    from app.services.connector_sync import BuiltinConnectorSyncError

    def fake_sync(*, connector, source, tenant_id, action_prefix):
        raise BuiltinConnectorSyncError(source, tenant_id, RuntimeError("boom"))

    monkeypatch.setattr(scheduler_worker, "sync_builtin_connector", fake_sync)

    with TestClient(app):
        results = scheduler_worker.run_scheduler_tick()

    assert len(results) == 1
    assert results[0]["ok"] is False
    assert results[0]["slug"] == "github"
    assert "boom" not in results[0]["error"]


def test_run_scheduler_tick_syncs_db_configured_tenant_builtin_connector(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_db_builtin.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED", False)

    from app.db.repositories.builtin_connector_secrets_repo import upsert_builtin_connector_secret

    calls = []

    def fake_sync(*, connector, source, tenant_id, action_prefix):
        calls.append((tenant_id, source, connector.token))
        return {"tenant_id": tenant_id, "processed": 0, "inserted": 0, "duplicates": 0, "rejected": 0}

    monkeypatch.setattr(scheduler_worker, "sync_builtin_connector", fake_sync)

    with TestClient(app):
        upsert_builtin_connector_secret(
            tenant_id="tenant_own_creds",
            source_type="github",
            config={"token": "own-github-token"},
            poll_interval_seconds=300,
        )
        results = scheduler_worker.run_scheduler_tick()

    assert calls == [("tenant_own_creds", "github", "own-github-token")]
    assert len(results) == 1
    assert results[0]["ok"] is True
    assert results[0]["tenant_id"] == "tenant_own_creds"


def test_run_scheduler_tick_syncs_multiple_tenants_same_source(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_multi_tenant.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED", False)

    from app.db.repositories.builtin_connector_secrets_repo import upsert_builtin_connector_secret

    calls = []

    def fake_sync(*, connector, source, tenant_id, action_prefix):
        calls.append((tenant_id, connector.token))
        return {"tenant_id": tenant_id, "processed": 0, "inserted": 0, "duplicates": 0, "rejected": 0}

    monkeypatch.setattr(scheduler_worker, "sync_builtin_connector", fake_sync)

    with TestClient(app):
        upsert_builtin_connector_secret(
            tenant_id="tenant_one", source_type="github", config={"token": "token-one"}, poll_interval_seconds=300
        )
        upsert_builtin_connector_secret(
            tenant_id="tenant_two", source_type="github", config={"token": "token-two"}, poll_interval_seconds=300
        )
        results = scheduler_worker.run_scheduler_tick()

    assert sorted(calls) == [("tenant_one", "token-one"), ("tenant_two", "token-two")]
    assert len(results) == 2


def test_run_scheduler_tick_syncs_db_configured_google_calendar(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_db_gcal.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_GOOGLE_CALENDAR_POLL_ENABLED", False)
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED", False)

    from app.db.repositories.builtin_connector_secrets_repo import upsert_builtin_connector_secret

    calls = []

    def fake_sync(*, tenant_id, calendar_id=None, token=None, client_id=None, client_secret=None, refresh_token=None, retry_policy=None, seeded_events=None):
        calls.append((tenant_id, calendar_id, token))
        return {"tenant_id": tenant_id, "processed": 0, "inserted": 0, "duplicates": 0, "rejected": 0}

    monkeypatch.setattr(scheduler_worker, "sync_google_calendar_connector", fake_sync)

    with TestClient(app):
        upsert_builtin_connector_secret(
            tenant_id="tenant_own_creds",
            source_type="google_calendar",
            config={"token": "own-gcal-token", "calendar_id": "team@example.invalid"},
            poll_interval_seconds=300,
        )
        results = scheduler_worker.run_scheduler_tick()

    assert calls == [("tenant_own_creds", "team@example.invalid", "own-gcal-token")]
    assert results[0]["ok"] is True
    assert results[0]["slug"] == "google_calendar"


def test_run_scheduler_tick_skips_legacy_env_path_when_db_row_exists_for_same_tenant(tmp_path, monkeypatch) -> None:
    session.DB_PATH = tmp_path / "scheduler_tick_dedupe.db"
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED", True)
    monkeypatch.setattr(scheduler_worker, "ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID", "tenant_shared")
    monkeypatch.setattr(scheduler_worker, "has_secret_value", lambda key: key == "ALLINO_GITHUB_TOKEN")

    from app.db.repositories.builtin_connector_secrets_repo import upsert_builtin_connector_secret

    calls = []

    def fake_sync(*, connector, source, tenant_id, action_prefix):
        calls.append((tenant_id, connector.token))
        return {"tenant_id": tenant_id, "processed": 0, "inserted": 0, "duplicates": 0, "rejected": 0}

    monkeypatch.setattr(scheduler_worker, "sync_builtin_connector", fake_sync)

    with TestClient(app):
        upsert_builtin_connector_secret(
            tenant_id="tenant_shared",
            source_type="github",
            config={"token": "db-token"},
            poll_interval_seconds=300,
        )
        results = scheduler_worker.run_scheduler_tick()

    # Only the DB-configured path should have run for tenant_shared/github, not
    # the legacy env path too -- otherwise this tenant/source pair would be
    # synced (and telemetry-recorded) twice per tick.
    assert calls == [("tenant_shared", "db-token")]
    assert len(results) == 1
