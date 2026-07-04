from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timezone
from typing import Any

from ..connectors.base import RetryPolicy
from ..connectors.discord_connector import DiscordConnector
from ..connectors.github_connector import GitHubConnector
from ..connectors.gitlab_connector import GitLabConnector
from ..connectors.jira_connector import JiraConnector
from ..connectors.linear_connector import LinearConnector
from ..connectors.rocketchat_connector import RocketChatConnector
from ..connectors.slack_connector import SlackConnector
from ..connectors.teams_connector import TeamsConnector
from ..connectors.telegram_connector import TelegramConnector
from ..connectors.zoom_connector import ZoomConnector
from ..core.config import (
    ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED,
    ALLINO_BUILTIN_CONNECTORS_POLL_INTERVAL_SECONDS,
    ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID,
    ALLINO_GOOGLE_CALENDAR_POLL_CALENDAR_ID,
    ALLINO_GOOGLE_CALENDAR_POLL_ENABLED,
    ALLINO_GOOGLE_CALENDAR_POLL_INTERVAL_SECONDS,
    ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID,
    ALLINO_SCHEDULER_WORKER_POLL_INTERVAL_SECONDS,
)
from ..core.secrets import has_secret_value
from ..db.repositories.builtin_connector_secrets_repo import (
    get_builtin_connector_secret,
    list_builtin_connector_secrets_with_polling,
)
from ..db.repositories.connectors_repo import get_connector
from ..db.repositories.generic_connectors_repo import list_generic_connectors_with_polling
from ..db.session import get_connection
from ..services.connector_sync import (
    BuiltinConnectorSyncError,
    GenericConnectorSyncError,
    GoogleCalendarSyncError,
    sync_builtin_connector,
    sync_generic_connector,
    sync_google_calendar_connector,
)

logger = logging.getLogger(__name__)

# (source_type, connector class, env var that must be set for this connector to be
# attempted). Google Calendar is handled separately above/below since it has its own
# dedicated poll-interval/calendar-id config predating this generic mechanism.
_BUILTIN_CONNECTOR_SPECS: list[tuple[str, type, str]] = [
    ("github", GitHubConnector, "ALLINO_GITHUB_TOKEN"),
    ("gitlab", GitLabConnector, "ALLINO_GITLAB_TOKEN"),
    ("jira", JiraConnector, "ALLINO_JIRA_TOKEN"),
    ("linear", LinearConnector, "ALLINO_LINEAR_TOKEN"),
    ("telegram", TelegramConnector, "ALLINO_TELEGRAM_BOT_TOKEN"),
    ("slack", SlackConnector, "ALLINO_SLACK_BOT_TOKEN"),
    ("discord", DiscordConnector, "ALLINO_DISCORD_BOT_TOKEN"),
    ("zoom", ZoomConnector, "ALLINO_ZOOM_TOKEN"),
    ("teams", TeamsConnector, "ALLINO_TEAMS_TOKEN"),
    ("rocketchat", RocketChatConnector, "ALLINO_ROCKETCHAT_TOKEN"),
]

# Per-tenant DB-configured secrets path (Sprint 31): connector class + which extra
# constructor kwargs (beyond tenant_id/token/retry_policy) to pull from the
# decrypted config blob, if present. Google Calendar is handled separately since it
# goes through sync_google_calendar_connector, not a bare connector class.
_BUILTIN_SOURCE_CONNECTOR_MAP: dict[str, tuple[type, tuple[str, ...]]] = {
    "github": (GitHubConnector, ()),
    "gitlab": (GitLabConnector, ("base_url",)),
    "jira": (JiraConnector, ("base_url",)),
    "linear": (LinearConnector, ()),
    "telegram": (TelegramConnector, ()),
    "slack": (SlackConnector, ("channel_id",)),
    "discord": (DiscordConnector, ("channel_id",)),
    "zoom": (ZoomConnector, ()),
    "teams": (TeamsConnector, ()),
    "rocketchat": (RocketChatConnector, ("user_id", "base_url", "channel_id")),
}


def _is_due(config: dict[str, Any], *, now: datetime) -> bool:
    interval = config.get("poll_interval_seconds")
    if not interval:
        return False

    connector_id = f"{config['tenant_id']}:generic:{config['slug']}"
    status = get_connector(connector_id)
    if status is None or not status.get("last_synced_at"):
        return True

    try:
        last_synced = datetime.fromisoformat(status["last_synced_at"])
    except ValueError:
        return True
    if last_synced.tzinfo is None:
        last_synced = last_synced.replace(tzinfo=timezone.utc)

    return (now - last_synced).total_seconds() >= interval


def _is_google_calendar_due(*, now: datetime) -> bool:
    """Google Calendar has no persisted per-tenant config row (unlike Generic HTTP
    Connectors), so polling is scoped to a single env-configured tenant/calendar --
    see ALLINO_GOOGLE_CALENDAR_POLL_* in core/config.py and the Sprint 19 board."""
    if not ALLINO_GOOGLE_CALENDAR_POLL_ENABLED or not ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID:
        return False

    connector_id = f"{ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID}:google_calendar"
    status = get_connector(connector_id)
    if status is None or not status.get("last_synced_at"):
        return True

    try:
        last_synced = datetime.fromisoformat(status["last_synced_at"])
    except ValueError:
        return True
    if last_synced.tzinfo is None:
        last_synced = last_synced.replace(tzinfo=timezone.utc)

    return (now - last_synced).total_seconds() >= ALLINO_GOOGLE_CALENDAR_POLL_INTERVAL_SECONDS


def _is_builtin_connector_due(source: str, tenant_id: str, *, now: datetime) -> bool:
    connector_id = f"{tenant_id}:{source}"
    status = get_connector(connector_id)
    if status is None or not status.get("last_synced_at"):
        return True

    try:
        last_synced = datetime.fromisoformat(status["last_synced_at"])
    except ValueError:
        return True
    if last_synced.tzinfo is None:
        last_synced = last_synced.replace(tzinfo=timezone.utc)

    return (now - last_synced).total_seconds() >= ALLINO_BUILTIN_CONNECTORS_POLL_INTERVAL_SECONDS


def run_scheduler_tick(*, now: datetime | None = None) -> list[dict[str, Any]]:
    """Sync every due generic connector, plus the env-configured Google Calendar tenant
    and built-in named connectors (GitHub/GitLab/Jira/etc.), each if enabled and due.
    Returns one result dict per connector run."""
    now = now or datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []

    for config in list_generic_connectors_with_polling():
        if not config.get("base_url"):
            continue
        if not _is_due(config, now=now):
            continue

        try:
            result = sync_generic_connector(
                config=config,
                tenant_id=config["tenant_id"],
                retry_policy=RetryPolicy(),
            )
            results.append({"tenant_id": config["tenant_id"], "slug": config["slug"], "ok": True, **result})
        except GenericConnectorSyncError as exc:
            logger.warning("scheduled sync failed for %s: %s", config["slug"], exc)
            results.append(
                {"tenant_id": config["tenant_id"], "slug": config["slug"], "ok": False, "error": str(exc)}
            )

    if _is_google_calendar_due(now=now):
        tenant_id = ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID
        try:
            result = sync_google_calendar_connector(
                tenant_id=tenant_id,
                calendar_id=ALLINO_GOOGLE_CALENDAR_POLL_CALENDAR_ID,
                retry_policy=RetryPolicy(),
            )
            results.append({"tenant_id": tenant_id, "slug": "google_calendar", "ok": True, **result})
        except GoogleCalendarSyncError as exc:
            logger.warning("scheduled sync failed for google_calendar: %s", exc)
            results.append(
                {"tenant_id": tenant_id, "slug": "google_calendar", "ok": False, "error": str(exc)}
            )

    if ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED and ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID:
        tenant_id = ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID
        for source, connector_cls, secret_key in _BUILTIN_CONNECTOR_SPECS:
            # A DB-configured secret for this exact (tenant, source) pair takes
            # precedence -- skip the env path so this pair isn't synced twice.
            if get_builtin_connector_secret(tenant_id=tenant_id, source_type=source) is not None:
                continue
            if not has_secret_value(secret_key):
                continue
            if not _is_builtin_connector_due(source, tenant_id, now=now):
                continue

            connector = connector_cls(tenant_id=tenant_id, retry_policy=RetryPolicy())
            try:
                result = sync_builtin_connector(
                    connector=connector,
                    source=source,
                    tenant_id=tenant_id,
                    action_prefix=f"connector.{source}.sync",
                )
                results.append({"tenant_id": tenant_id, "slug": source, "ok": True, **result})
            except BuiltinConnectorSyncError as exc:
                logger.warning("scheduled sync failed for %s: %s", source, exc)
                results.append({"tenant_id": tenant_id, "slug": source, "ok": False, "error": str(exc)})

    # Per-tenant DB-configured secrets (Sprint 31) -- supports any number of
    # tenants, each bringing their own credentials, unlike the single-env-tenant
    # paths above.
    for row in list_builtin_connector_secrets_with_polling():
        tenant_id = row["tenant_id"]
        source = row["source_type"]
        config = row["config"]
        if not _is_builtin_connector_due(source, tenant_id, now=now):
            continue

        if source == "google_calendar":
            try:
                result = sync_google_calendar_connector(
                    tenant_id=tenant_id,
                    calendar_id=config.get("calendar_id"),
                    token=config.get("token"),
                    retry_policy=RetryPolicy(),
                )
                results.append({"tenant_id": tenant_id, "slug": source, "ok": True, **result})
            except GoogleCalendarSyncError as exc:
                logger.warning("scheduled sync failed for tenant %s google_calendar: %s", tenant_id, exc)
                results.append({"tenant_id": tenant_id, "slug": source, "ok": False, "error": str(exc)})
            continue

        connector_cls, extra_fields = _BUILTIN_SOURCE_CONNECTOR_MAP[source]
        extra_kwargs = {field: config[field] for field in extra_fields if config.get(field)}
        connector = connector_cls(tenant_id=tenant_id, token=config.get("token"), retry_policy=RetryPolicy(), **extra_kwargs)
        try:
            result = sync_builtin_connector(
                connector=connector,
                source=source,
                tenant_id=tenant_id,
                action_prefix=f"connector.{source}.sync",
            )
            results.append({"tenant_id": tenant_id, "slug": source, "ok": True, **result})
        except BuiltinConnectorSyncError as exc:
            logger.warning("scheduled sync failed for tenant %s %s: %s", tenant_id, source, exc)
            results.append({"tenant_id": tenant_id, "slug": source, "ok": False, "error": str(exc)})

    return results


def check_worker_health() -> tuple[bool, str]:
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True, "ok"
    except Exception as exc:
        return False, f"database connectivity failed: {exc}"


def run_scheduler_loop(poll_interval_seconds: float | None = None) -> None:
    interval = (
        poll_interval_seconds
        if poll_interval_seconds is not None
        else ALLINO_SCHEDULER_WORKER_POLL_INTERVAL_SECONDS
    )
    logger.info("Starting scheduler worker, checking due connectors every %.1fs", interval)
    while True:
        try:
            run_scheduler_tick()
        except Exception:  # pragma: no cover - resilience path
            logger.exception("scheduler tick failed")
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="ALLinO scheduler worker")
    parser.add_argument("--healthcheck", action="store_true", help="Check DB connectivity and exit")
    parser.add_argument("--once", action="store_true", help="Run a single scheduler tick and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.healthcheck:
        ok, message = check_worker_health()
        if ok:
            print("ok")
            return
        raise RuntimeError(message)

    if args.once:
        results = run_scheduler_tick()
        logger.info("Scheduler tick complete: %d connector(s) synced", len(results))
        return

    run_scheduler_loop()


if __name__ == "__main__":
    main()
