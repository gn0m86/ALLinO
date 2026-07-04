from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..connectors.base import RetryPolicy
from ..connectors.generic_http_connector import GenericHttpConnector
from ..connectors.google_calendar_connector import GoogleCalendarConnector
from ..db.repositories.connector_runs_repo import append_connector_run
from ..db.repositories.connectors_repo import upsert_connector_status
from ..services.audit import log_custom
from ..services.event_bus import process_connector_events
from ..services.ingestion_processor import process_connector_batch
from ..services.metrics import get_metrics_store


class GenericConnectorSyncError(RuntimeError):
    def __init__(self, slug: str, cause: Exception) -> None:
        super().__init__(f"generic connector '{slug}' sync failed")
        self.slug = slug
        self.__cause__ = cause


class GoogleCalendarSyncError(RuntimeError):
    def __init__(self, tenant_id: str, cause: Exception) -> None:
        super().__init__(f"google_calendar sync failed for tenant '{tenant_id}'")
        self.tenant_id = tenant_id
        self.__cause__ = cause


class BuiltinConnectorSyncError(RuntimeError):
    def __init__(self, source: str, tenant_id: str, cause: Exception) -> None:
        super().__init__(f"{source} sync failed for tenant '{tenant_id}'")
        self.source = source
        self.tenant_id = tenant_id
        self.__cause__ = cause


def record_batch_result(
    *,
    tenant_id: str,
    source: str,
    action_prefix: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    sync_time = datetime.now(timezone.utc).isoformat()
    try:
        counts, bus_meta = process_connector_events(
            tenant_id=tenant_id,
            source=source,
            action_prefix=action_prefix,
            events=events,
            processor=lambda batch, t_id, a_prefix: process_connector_batch(
                events=batch,
                tenant_id=t_id,
                action_prefix=a_prefix,
            ),
        )
        upsert_connector_status(
            tenant_id=tenant_id,
            source_type=source,
            status="healthy",
            last_synced_at=sync_time,
            last_error=None,
            last_processed=int(counts["processed"]),
            last_inserted=int(counts["inserted"]),
            last_duplicates=int(counts["duplicates"]),
            last_rejected=int(counts["rejected"]),
        )
        append_connector_run(
            tenant_id=tenant_id,
            source_type=source,
            status="healthy",
            synced_at=sync_time,
            processed=int(counts["processed"]),
            inserted=int(counts["inserted"]),
            duplicates=int(counts["duplicates"]),
            rejected=int(counts["rejected"]),
            error=None,
        )
        get_metrics_store().record_sync(
            tenant_id=tenant_id,
            source=source,
            processed=counts["processed"],
            inserted=counts["inserted"],
            duplicates=counts["duplicates"],
            rejected=counts["rejected"],
            total_lag_ms=float(counts["total_lag_ms"]),
            lag_samples=int(counts["lag_samples"]),
            health="healthy",
            retry_count=0,
        )
        public_counts = {k: counts[k] for k in ("processed", "inserted", "duplicates", "rejected")}
        log_custom(
            tenant_id=tenant_id,
            action=f"{action_prefix}.batch",
            metadata={**public_counts, "event_bus": bus_meta},
        )
        return {"tenant_id": tenant_id, **public_counts, "event_bus": bus_meta["mode"]}
    except Exception as exc:
        upsert_connector_status(
            tenant_id=tenant_id,
            source_type=source,
            status="error",
            last_synced_at=sync_time,
            last_error=str(exc),
            last_processed=0,
            last_inserted=0,
            last_duplicates=0,
            last_rejected=0,
        )
        append_connector_run(
            tenant_id=tenant_id,
            source_type=source,
            status="error",
            synced_at=sync_time,
            processed=0,
            inserted=0,
            duplicates=0,
            rejected=0,
            error=str(exc),
        )
        log_custom(tenant_id=tenant_id, action=f"{action_prefix}.error", metadata={"error": str(exc)})
        raise


def sync_generic_connector(
    *,
    config: dict[str, Any],
    tenant_id: str,
    retry_policy: RetryPolicy | None = None,
    seeded_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fetch + ingest one generic connector's events. Shared by the manual sync endpoint
    and the scheduler worker so both go through the exact same code path."""
    connector = GenericHttpConnector(
        tenant_id=tenant_id,
        slug=config["slug"],
        base_url=config["base_url"],
        auth_method=config["auth_method"],
        auth_header_name=config["auth_header_name"],
        field_mapping=config["field_mapping"],
        retry_policy=retry_policy or RetryPolicy(),
        seeded_items=seeded_items or [],
    )
    source = f"generic:{config['slug']}"
    try:
        connector.start()
        events = list(connector.fetch_events())
    except Exception as exc:
        connector.stop()
        upsert_connector_status(
            tenant_id=tenant_id,
            source_type=source,
            status="error",
            last_synced_at=datetime.now(timezone.utc).isoformat(),
            last_error=str(exc),
        )
        raise GenericConnectorSyncError(config["slug"], exc) from exc

    try:
        return record_batch_result(
            tenant_id=tenant_id,
            source=source,
            action_prefix=f"connector.generic.{config['slug']}.sync",
            events=events,
        )
    except Exception as exc:
        raise GenericConnectorSyncError(config["slug"], exc) from exc
    finally:
        connector.stop()


def sync_google_calendar_connector(
    *,
    tenant_id: str,
    calendar_id: str | None = None,
    token: str | None = None,
    retry_policy: RetryPolicy | None = None,
    seeded_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fetch + ingest one tenant's Google Calendar events. Shared by the manual sync
    endpoint and the scheduler worker so both go through the exact same code path."""
    connector = GoogleCalendarConnector(
        tenant_id=tenant_id,
        token=token,
        calendar_id=calendar_id,
        retry_policy=retry_policy or RetryPolicy(),
        seeded_events=seeded_events or [],
    )
    try:
        connector.start()
        events = list(connector.fetch_events())
    except Exception as exc:
        connector.stop()
        upsert_connector_status(
            tenant_id=tenant_id,
            source_type="google_calendar",
            status="error",
            last_synced_at=datetime.now(timezone.utc).isoformat(),
            last_error=str(exc),
        )
        raise GoogleCalendarSyncError(tenant_id, exc) from exc

    try:
        return record_batch_result(
            tenant_id=tenant_id,
            source="google_calendar",
            action_prefix="connector.google_calendar.sync",
            events=events,
        )
    except Exception as exc:
        raise GoogleCalendarSyncError(tenant_id, exc) from exc
    finally:
        connector.stop()


def sync_builtin_connector(
    *,
    connector: Any,
    source: str,
    tenant_id: str,
    action_prefix: str,
) -> dict[str, Any]:
    """Fetch + ingest one built-in named connector's events (GitHub, GitLab, Jira,
    Linear, Telegram, Slack, Discord, Zoom, Teams, Rocket.Chat). Mirrors
    `api/ingestion.py`'s `_run_connector_sync` (used by the manual sync endpoints)
    but reusable from the scheduler worker, which has no HTTP request/response to
    build on."""
    try:
        connector.start()
        events = list(connector.fetch_events())
    except Exception as exc:
        connector.stop()
        upsert_connector_status(
            tenant_id=tenant_id,
            source_type=source,
            status="error",
            last_synced_at=datetime.now(timezone.utc).isoformat(),
            last_error=str(exc),
        )
        raise BuiltinConnectorSyncError(source, tenant_id, exc) from exc

    try:
        return record_batch_result(
            tenant_id=tenant_id,
            source=source,
            action_prefix=action_prefix,
            events=events,
        )
    except Exception as exc:
        raise BuiltinConnectorSyncError(source, tenant_id, exc) from exc
    finally:
        connector.stop()
