from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ..connectors.base import RetryPolicy

from ..connectors.github_connector import GitHubConnector
from ..connectors.gitlab_connector import GitLabConnector
from ..connectors.jira_connector import JiraConnector
from ..connectors.linear_connector import LinearConnector
from ..connectors.slack_connector import SlackConnector
from ..connectors.telegram_connector import TelegramConnector
from ..connectors.discord_connector import DiscordConnector
from ..connectors.zoom_connector import ZoomConnector
from ..connectors.teams_connector import TeamsConnector
from ..connectors.google_calendar_connector import GoogleCalendarConnector
from ..connectors.rocketchat_connector import RocketChatConnector
from ..core.security import (
    require_api_key,
    require_connector_sync_permission,
    require_ingestion_read_permission,
)
from ..core.secrets import has_secret_value
from ..core.tenant import resolve_tenant_id
from ..db.repositories.audit_repo import count_audit, list_audit
from ..db.repositories.connectors_repo import list_connectors, upsert_connector_status
from ..db.repositories.connector_runs_repo import append_connector_run, list_connector_runs
from ..db.repositories.messages_repo import (
    add_if_new,
    count_messages,
    list_messages,
    list_messages_page,
    search_messages,
)
from ..domain.events import InboxMessage, UnifiedEvent
from ..services.audit import log_custom, log_ingestion_event
from ..services.dedup import dedup_key
from ..services.digest import build_digest
from ..services.event_bus import process_connector_events
from ..services.ingestion_processor import process_connector_batch
from ..services.metrics import get_metrics_store
from ..services.normalizer import normalize_event

router = APIRouter(
    prefix="/api/v1/ingestion",
    tags=["ingestion"],
    dependencies=[Depends(require_api_key)],
)


class ConnectorRetryOptions(BaseModel):
    retry_max_attempts: int | None = Field(default=None, ge=1, le=10)
    retry_backoff_seconds: float | None = Field(default=None, ge=0.0, le=5.0)


class GitHubSyncRequest(ConnectorRetryOptions):
    seeded_notifications: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None


class GitLabSyncRequest(ConnectorRetryOptions):
    seeded_notifications: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None
    base_url: str | None = None


class LinearSyncRequest(ConnectorRetryOptions):
    seeded_events: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None


class JiraSyncRequest(ConnectorRetryOptions):
    seeded_issues: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None
    base_url: str | None = None


class TelegramSyncRequest(ConnectorRetryOptions):
    seeded_updates: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None


class SlackSyncRequest(ConnectorRetryOptions):
    seeded_messages: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None
    channel_id: str | None = None


class DiscordSyncRequest(ConnectorRetryOptions):
    seeded_messages: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None
    channel_id: str | None = None


class ZoomSyncRequest(ConnectorRetryOptions):
    seeded_events: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None


class TeamsSyncRequest(ConnectorRetryOptions):
    seeded_messages: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None


class GoogleCalendarSyncRequest(ConnectorRetryOptions):
    seeded_events: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None
    calendar_id: str | None = None


class RocketChatSyncRequest(ConnectorRetryOptions):
    seeded_messages: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None
    channel_id: str | None = None
    base_url: str | None = None


class InboxPageResponse(BaseModel):
    items: list[InboxMessage]
    next_cursor: str | None = None


def _assert_tenant_match(event_tenant: str, resolved_tenant: str) -> None:
    """Reject events whose tenantId doesn't match the authenticated tenant context."""
    if event_tenant != resolved_tenant:
        raise HTTPException(
            status_code=403,
            detail=(
                f"tenantId '{event_tenant}' in payload does not match "
                f"authenticated tenant '{resolved_tenant}'"
            ),
        )


def _build_retry_policy(payload: ConnectorRetryOptions) -> RetryPolicy:
    if payload.retry_max_attempts is None and payload.retry_backoff_seconds is None:
        return RetryPolicy()

    return RetryPolicy(
        max_attempts=payload.retry_max_attempts or RetryPolicy().max_attempts,
        backoff_seconds=payload.retry_backoff_seconds
        if payload.retry_backoff_seconds is not None
        else RetryPolicy().backoff_seconds,
    )


@router.post("/validate")
def validate_event(
    event: UnifiedEvent,
    tenant_id: str = Depends(resolve_tenant_id),
) -> dict:
    _assert_tenant_match(event.tenantId, tenant_id)
    normalized = normalize_event(event)
    return {
        "status": "valid",
        "normalized": normalized.model_dump(mode="json"),
    }


@router.post("/events")
def ingest_event(
    event: UnifiedEvent,
    tenant_id: str = Depends(resolve_tenant_id),
) -> dict[str, str]:
    _assert_tenant_match(event.tenantId, tenant_id)
    normalized = normalize_event(event)
    key = dedup_key(event.tenantId, event.sourceType, event.externalId)
    inserted = add_if_new(key, normalized)
    status = "inserted" if inserted else "duplicate"
    log_ingestion_event(
        tenant_id=event.tenantId,
        action="ingestion.event",
        event_id=event.eventId,
        source=event.sourceType,
        external_id=event.externalId,
        status=status,
    )
    return {"status": status}


def _run_connector_sync(
    *,
    connector: Any,
    source: str,
    tenant_id: str,
    cursor: str | None,
    action_prefix: str,
) -> dict[str, int | str]:
    sync_time = datetime.now(timezone.utc).isoformat()
    try:
        connector.start()
        events = list(connector.fetch_events(cursor=cursor))
        health = connector.health()
        connector_health = health.status

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
            status=connector_health,
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
            status=connector_health,
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
            health=connector_health,
            retry_count=int(health.details.get("retry_count", 0)),
        )

        public_counts = {k: counts[k] for k in ("processed", "inserted", "duplicates", "rejected")}
        log_custom(
            tenant_id=tenant_id,
            action=f"{action_prefix}.batch",
            metadata={**public_counts, "health": connector_health, "event_bus": bus_meta},
        )
        return {"tenant_id": tenant_id, **public_counts, "health": connector_health, "event_bus": bus_meta["mode"]}
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
        log_custom(
            tenant_id=tenant_id,
            action=f"{action_prefix}.error",
            metadata={"error": str(exc)},
        )
        raise HTTPException(status_code=502, detail=f"{source} connector sync failed") from exc
    finally:
        try:
            connector.stop()
        except Exception:
            pass


@router.post("/connectors/github/sync")
def sync_github_connector(
    payload: GitHubSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = GitHubConnector(
        tenant_id=tenant_id,
        token=connector_token,
        seeded_notifications=payload.seeded_notifications,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="github",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.github.sync",
    )


@router.post("/connectors/linear/sync")
def sync_linear_connector(
    payload: LinearSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = LinearConnector(
        tenant_id=tenant_id,
        token=connector_token,
        seeded_events=payload.seeded_events,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="linear",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.linear.sync",
    )


@router.post("/connectors/gitlab/sync")
def sync_gitlab_connector(
    payload: GitLabSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = GitLabConnector(
        tenant_id=tenant_id,
        token=connector_token,
        base_url=payload.base_url,
        seeded_notifications=payload.seeded_notifications,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="gitlab",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.gitlab.sync",
    )


@router.post("/connectors/jira/sync")
def sync_jira_connector(
    payload: JiraSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = JiraConnector(
        tenant_id=tenant_id,
        token=connector_token,
        base_url=payload.base_url,
        seeded_issues=payload.seeded_issues,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="jira",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.jira.sync",
    )


@router.post("/connectors/telegram/sync")
def sync_telegram_connector(
    payload: TelegramSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = TelegramConnector(
        tenant_id=tenant_id,
        token=connector_token,
        seeded_updates=payload.seeded_updates,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="telegram",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.telegram.sync",
    )


@router.post("/connectors/slack/sync")
def sync_slack_connector(
    payload: SlackSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = SlackConnector(
        tenant_id=tenant_id,
        token=connector_token,
        channel_id=payload.channel_id,
        seeded_messages=payload.seeded_messages,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="slack",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.slack.sync",
    )


@router.post("/connectors/discord/sync")
def sync_discord_connector(
    payload: DiscordSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = DiscordConnector(
        tenant_id=tenant_id,
        token=connector_token,
        channel_id=payload.channel_id,
        seeded_messages=payload.seeded_messages,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="discord",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.discord.sync",
    )


@router.post("/connectors/zoom/sync")
def sync_zoom_connector(
    payload: ZoomSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = ZoomConnector(
        tenant_id=tenant_id,
        token=connector_token,
        seeded_events=payload.seeded_events,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="zoom",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.zoom.sync",
    )


@router.post("/connectors/teams/sync")
def sync_teams_connector(
    payload: TeamsSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = TeamsConnector(
        tenant_id=tenant_id,
        token=connector_token,
        seeded_messages=payload.seeded_messages,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="teams",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.teams.sync",
    )


@router.post("/connectors/google_calendar/sync")
def sync_google_calendar_connector(
    payload: GoogleCalendarSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = GoogleCalendarConnector(
        tenant_id=tenant_id,
        token=connector_token,
        calendar_id=payload.calendar_id,
        seeded_events=payload.seeded_events,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="google_calendar",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.google_calendar.sync",
    )


@router.post("/connectors/rocketchat/sync")
def sync_rocketchat_connector(
    payload: RocketChatSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
    x_connector_token: str | None = Header(default=None, alias="X-Connector-Token"),
) -> dict[str, int | str]:
    connector_token = x_connector_token
    retry_policy = _build_retry_policy(payload)
    connector = RocketChatConnector(
        tenant_id=tenant_id,
        token=connector_token,
        base_url=payload.base_url,
        channel_id=payload.channel_id,
        seeded_messages=payload.seeded_messages,
        retry_policy=retry_policy,
    )
    return _run_connector_sync(
        connector=connector,
        source="rocketchat",
        tenant_id=tenant_id,
        cursor=payload.cursor,
        action_prefix="connector.rocketchat.sync",
    )


@router.get("/inbox", response_model=list[InboxMessage])
def inbox(
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = Query(default=None),
    archived: bool = Query(default=False),
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[InboxMessage]:
    try:
        return list_messages(tenant_id=tenant_id, limit=limit, cursor=cursor, archived_only=archived)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid inbox cursor") from exc


@router.get("/search", response_model=list[InboxMessage])
def search_inbox(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[InboxMessage]:
    """Exact (case-insensitive substring) search over active messages only --
    archived/snoozed messages are out of scope, matching the normal inbox's
    default view. See messages_repo.search_messages for why this isn't a
    database-level full-text index."""
    return search_messages(tenant_id=tenant_id, query=q, limit=limit)


class DigestResponse(BaseModel):
    tenant_id: str
    since_hours: int
    total: int
    by_source: dict[str, int]
    by_priority: dict[str, int]
    highlights: list[InboxMessage]


@router.get("/digest", response_model=DigestResponse)
def ingestion_digest(
    hours: int = Query(default=24, ge=1, le=720),
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> DigestResponse:
    """Rule-based activity summary (counts by source/priority + top high-priority
    highlights) over active messages ingested in the last `hours`. No AI/external
    calls involved -- pure aggregation over data already in the local database."""
    return DigestResponse(**build_digest(tenant_id=tenant_id, since_hours=hours))


@router.get("/inbox/page", response_model=InboxPageResponse)
def inbox_page(
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = Query(default=None),
    archived: bool = Query(default=False),
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> InboxPageResponse:
    try:
        items, next_cursor = list_messages_page(
            tenant_id=tenant_id, limit=limit, cursor=cursor, archived_only=archived
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid inbox cursor") from exc
    return InboxPageResponse(items=items, next_cursor=next_cursor)


@router.post("/seed")
def seed_events(
    tenant_id: str = Depends(resolve_tenant_id),
    source: str = Query(default="seed"),
    count: int = Query(default=5, ge=1, le=100),
) -> dict[str, int | str]:
    inserted = 0
    duplicates = 0
    safe_count = count

    for i in range(safe_count):
        now = datetime.now(timezone.utc)
        event = UnifiedEvent(
            eventId=str(uuid4()),
            tenantId=tenant_id,
            sourceType=source,
            externalId=f"{source}-{i}-{int(now.timestamp())}",
            timestamp=now,
            payload={"text": f"Seed event {i + 1}"},
            schemaVersion="1.0.0",
        )

        normalized = normalize_event(event)
        key = dedup_key(event.tenantId, event.sourceType, event.externalId)
        added = add_if_new(key, normalized)
        if added:
            inserted += 1
            status = "inserted"
        else:
            duplicates += 1
            status = "duplicate"

        log_ingestion_event(
            tenant_id=event.tenantId,
            action="ingestion.seed",
            event_id=event.eventId,
            source=event.sourceType,
            external_id=event.externalId,
            status=status,
        )

    log_custom(
        tenant_id=tenant_id,
        action="ingestion.seed.batch",
        metadata={"requested": count, "processed": safe_count},
    )

    return {
        "tenant_id": tenant_id,
        "processed": safe_count,
        "inserted": inserted,
        "duplicates": duplicates,
    }


@router.get("/audit")
def audit(
    limit: int = Query(default=100, ge=1, le=1000),
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[dict]:
    return list_audit(tenant_id=tenant_id, limit=limit)


@router.get("/stats")
def ingestion_stats(
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> dict[str, int]:
    return {
        "inbox_count": count_messages(tenant_id=tenant_id),
        "audit_count": count_audit(tenant_id=tenant_id),
    }


@router.get("/metrics")
def ingestion_metrics(
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> dict:
    """Observability minimum: per-connector ingestion lag, retry/health, and event outcome counts."""
    return get_metrics_store().snapshot(tenant_id)


@router.get("/connectors")
def ingestion_connectors(
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[dict[str, Any]]:
    """Return connector registry state for the authenticated tenant."""
    return list_connectors(tenant_id=tenant_id)


@router.get("/connectors/capabilities")
def ingestion_connector_capabilities(
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[dict[str, Any]]:
    """Return connector capability matrix for UI source rendering."""
    _ = tenant_id
    github_configured = has_secret_value("ALLINO_GITHUB_TOKEN")
    gitlab_configured = has_secret_value("ALLINO_GITLAB_TOKEN")
    jira_configured = has_secret_value("ALLINO_JIRA_TOKEN")
    linear_configured = has_secret_value("ALLINO_LINEAR_TOKEN")
    telegram_configured = has_secret_value("ALLINO_TELEGRAM_BOT_TOKEN")
    slack_configured = has_secret_value("ALLINO_SLACK_BOT_TOKEN") and has_secret_value("ALLINO_SLACK_CHANNEL_ID")
    discord_configured = has_secret_value("ALLINO_DISCORD_BOT_TOKEN") and has_secret_value("ALLINO_DISCORD_CHANNEL_ID")
    zoom_configured = has_secret_value("ALLINO_ZOOM_TOKEN")
    teams_configured = has_secret_value("ALLINO_TEAMS_TOKEN")
    google_calendar_configured = has_secret_value("ALLINO_GOOGLE_CALENDAR_TOKEN")
    # ALLINO_ROCKETCHAT_CHANNEL_ID is intentionally not required here -- when unset,
    # the connector watches every room the configured user belongs to instead of one
    # specific channel (see RocketChatConnector._fetch_messages_from_api).
    rocketchat_configured = (
        has_secret_value("ALLINO_ROCKETCHAT_TOKEN")
        and has_secret_value("ALLINO_ROCKETCHAT_USER_ID")
        and has_secret_value("ALLINO_ROCKETCHAT_BASE_URL")
    )

    return [
        {
            "source_type": "github",
            "available": True,
            "configured": github_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "gitlab",
            "available": True,
            "configured": gitlab_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "jira",
            "available": True,
            "configured": jira_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "linear",
            "available": True,
            "configured": linear_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "telegram",
            "available": True,
            "configured": telegram_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "slack",
            "available": True,
            "configured": slack_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "discord",
            "available": True,
            "configured": discord_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "zoom",
            "available": True,
            "configured": zoom_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "teams",
            "available": True,
            "configured": teams_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "google_calendar",
            "available": True,
            "configured": google_calendar_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
        {
            "source_type": "rocketchat",
            "available": True,
            "configured": rocketchat_configured,
            "requires_secret": True,
            "sync_supported": True,
        },
    ]


@router.get("/connectors/runs")
def ingestion_connector_runs(
    tenant_id: str = Depends(resolve_tenant_id),
    limit: int = Query(default=20, ge=1, le=200),
    source: str | None = Query(default=None),
    _: None = Depends(require_ingestion_read_permission),
) -> list[dict[str, Any]]:
    """Return recent connector sync runs for the authenticated tenant."""
    source_type = source.strip().lower() if source else None
    return list_connector_runs(
        tenant_id=tenant_id,
        limit=limit,
        source_type=source_type,
    )
