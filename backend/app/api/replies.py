from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ..connectors.discord_connector import send_discord_reply
from ..connectors.github_connector import send_github_reply
from ..connectors.gitlab_connector import send_gitlab_reply
from ..connectors.jira_connector import send_jira_reply
from ..connectors.linear_connector import send_linear_reply
from ..connectors.rocketchat_connector import send_rocketchat_reply
from ..connectors.slack_connector import send_slack_reply
from ..connectors.telegram_connector import send_telegram_reply
from ..core.secrets import get_secret_value
from ..core.security import require_ingestion_read_permission, require_reply_permission
from ..core.tenant import resolve_tenant_id
from ..db.repositories.builtin_connector_secrets_repo import get_builtin_connector_secret
from ..db.repositories.messages_repo import get_message
from ..db.repositories.outbound_replies_repo import append_outbound_reply, list_outbound_replies
from ..services.audit import log_custom

router = APIRouter(prefix="/api/v1/ingestion", tags=["replies"])

_REPLY_TOKEN_ENV_KEYS: dict[str, str] = {
    "telegram": "ALLINO_TELEGRAM_BOT_TOKEN",
    "slack": "ALLINO_SLACK_BOT_TOKEN",
    "discord": "ALLINO_DISCORD_BOT_TOKEN",
    "rocketchat": "ALLINO_ROCKETCHAT_TOKEN",
    "github": "ALLINO_GITHUB_TOKEN",
    "gitlab": "ALLINO_GITLAB_TOKEN",
    "jira": "ALLINO_JIRA_TOKEN",
    "linear": "ALLINO_LINEAR_TOKEN",
}

_REPLY_SENDERS: dict[str, Callable[..., dict[str, Any]]] = {
    "telegram": send_telegram_reply,
    "slack": send_slack_reply,
    "discord": send_discord_reply,
    "rocketchat": send_rocketchat_reply,
    "github": send_github_reply,
    "gitlab": send_gitlab_reply,
    "jira": send_jira_reply,
    "linear": send_linear_reply,
}

# Rocket.Chat's REST API needs a token+user-id *pair* plus a self-hosted base
# URL, unlike every other reply source's single bot token — checked here so a
# pure misconfiguration fails closed with 503, not a spurious 502 delivery
# failure recorded as a failed attempt.
_REPLY_EXTRA_CONFIG_ENV_KEYS: dict[str, list[str]] = {
    "rocketchat": ["ALLINO_ROCKETCHAT_USER_ID", "ALLINO_ROCKETCHAT_BASE_URL"],
}

# GitHub/GitLab: external_id is the notification id, not the issue/PR itself
# — the address needed to comment only exists in messages.reply_target
# (populated at ingest time, see services/normalizer.py). A message ingested
# before that column existed, or a notification whose subject wasn't a
# commentable issue/PR, has no reply_target — reject with 400 (this specific
# message can't be replied to), not the 503 "not configured" path.
_REQUIRES_REPLY_TARGET = {"github", "gitlab"}

# Source-specific extra fields (beyond token) a reply send needs, read from a
# tenant's own DB-stored builtin_connector_secrets config -- mirrors
# connector_sync.BUILTIN_SOURCE_CONNECTOR_MAP's extra_fields for the sources
# reply actually supports.
_REPLY_EXTRA_CONFIG_FIELDS: dict[str, tuple[str, ...]] = {
    "rocketchat": ("user_id", "base_url"),
    "gitlab": ("base_url",),
    "jira": ("base_url",),
}


def _resolve_reply_credentials(source: str, tenant_id: str) -> dict[str, str] | None:
    """Env/Vault first (the original single-tenant path), falling back to the
    tenant's own DB-stored builtin connector secret (Sprint 31 "Your Own
    Credentials") if no env token is set. Sync already reads from the DB
    secret via connector_sync.py -- reply never did, so a tenant using only
    DB-stored credentials could sync but never got a working reply."""
    token = get_secret_value(_REPLY_TOKEN_ENV_KEYS[source])
    extra_missing = any(
        not get_secret_value(key) for key in _REPLY_EXTRA_CONFIG_ENV_KEYS.get(source, [])
    )
    if token and not extra_missing:
        creds = {"token": token}
        if source == "rocketchat":
            creds["user_id"] = get_secret_value("ALLINO_ROCKETCHAT_USER_ID") or ""
            creds["base_url"] = get_secret_value("ALLINO_ROCKETCHAT_BASE_URL") or ""
        return creds

    row = get_builtin_connector_secret(tenant_id=tenant_id, source_type=source)
    if row is None:
        return None
    config = row["config"]
    db_token = config.get("token")
    if not db_token:
        return None
    required_extra = _REPLY_EXTRA_CONFIG_FIELDS.get(source, ())
    if source == "rocketchat" and not all(config.get(field) for field in required_extra):
        return None
    creds = {"token": db_token}
    for field in required_extra:
        if config.get(field):
            creds[field] = config[field]
    return creds


class ReplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=4000)


@router.post("/messages/{event_id}/reply")
def send_reply(
    event_id: str,
    payload: ReplyRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_reply_permission),
) -> dict[str, Any]:
    message = get_message(tenant_id=tenant_id, event_id=event_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    source = message.source
    if source not in _REPLY_SENDERS:
        raise HTTPException(status_code=400, detail=f"Reply is not supported for source '{source}'")

    if source in _REQUIRES_REPLY_TARGET and not message.reply_target:
        raise HTTPException(
            status_code=400,
            detail=f"This '{source}' message can't be replied to (no reply target recorded for it)",
        )

    creds = _resolve_reply_credentials(source, tenant_id)
    if creds is None:
        raise HTTPException(status_code=503, detail=f"Reply is not configured for source '{source}'")

    send_kwargs: dict[str, Any] = {"token": creds["token"], "external_id": message.external_id, "text": payload.text}
    if source in _REQUIRES_REPLY_TARGET:
        send_kwargs["reply_target"] = message.reply_target
    for field in _REPLY_EXTRA_CONFIG_FIELDS.get(source, ()):
        if creds.get(field):
            send_kwargs[field] = creds[field]

    try:
        _REPLY_SENDERS[source](**send_kwargs)
    except Exception as exc:
        append_outbound_reply(
            tenant_id=tenant_id,
            event_id=event_id,
            source=source,
            external_id=message.external_id,
            text=payload.text,
            status="failed",
            error=str(exc),
        )
        log_custom(
            tenant_id=tenant_id,
            action="message.reply.failed",
            metadata={"event_id": event_id, "source": source, "error": str(exc)},
        )
        raise HTTPException(status_code=502, detail=f"Reply delivery to '{source}' failed") from exc

    append_outbound_reply(
        tenant_id=tenant_id,
        event_id=event_id,
        source=source,
        external_id=message.external_id,
        text=payload.text,
        status="sent",
    )
    log_custom(
        tenant_id=tenant_id,
        action="message.reply.sent",
        metadata={"event_id": event_id, "source": source},
    )
    return {"status": "sent", "event_id": event_id, "source": source}


@router.get("/replies")
def list_replies(
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[dict[str, Any]]:
    return list_outbound_replies(tenant_id=tenant_id, limit=limit)
