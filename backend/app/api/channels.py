import os
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..connectors.rocketchat_connector import get_dm_counterpart_utc_offset, get_own_rocketchat_username
from ..core.secrets import get_secret_value
from ..core.security import require_ingestion_read_permission, require_message_actions_permission
from ..core.tenant import resolve_tenant_id
from ..db.repositories.messages_repo import list_thread_messages, list_thread_summaries
from ..db.repositories.thread_read_repo import get_read_state, mark_thread_read
from ..domain.events import InboxMessage
from ..services.audit import log_custom

router = APIRouter(prefix="/api/v1/ingestion", tags=["channels"])


class ChannelSummary(BaseModel):
    thread_key: str
    source: str
    channel_kind: str | None
    channel_team: str | None
    latest: InboxMessage
    unread: bool


@router.get("/channels", response_model=list[ChannelSummary])
def list_channels(
    source: str | None = Query(default=None),
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[ChannelSummary]:
    """One row per channel/DM (chat-shaped sources only) -- the channel-browser
    view's list, grouping messages the way Rocket.Chat's own sidebar does
    (Teams / Channels / Direct messages), instead of one row per message."""
    summaries = list_thread_summaries(tenant_id=tenant_id, source=source)
    read_state = get_read_state(tenant_id=tenant_id)

    results: list[ChannelSummary] = []
    for message in summaries:
        last_read_at = read_state.get(message.thread_key)
        unread = last_read_at is None or message.timestamp.isoformat() > last_read_at
        results.append(
            ChannelSummary(
                thread_key=message.thread_key,
                source=message.source,
                channel_kind=message.channel_kind,
                channel_team=message.channel_team,
                latest=message,
                unread=unread,
            )
        )
    return results


@router.get("/threads/{thread_key}/messages", response_model=list[InboxMessage])
def get_thread_messages(
    thread_key: str,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[InboxMessage]:
    """Full chat transcript for one channel/DM, oldest first."""
    return list_thread_messages(tenant_id=tenant_id, thread_key=thread_key)


@router.post("/threads/{thread_key}/read")
def mark_thread_as_read(
    thread_key: str,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_message_actions_permission),
) -> dict[str, Any]:
    mark_thread_read(tenant_id=tenant_id, thread_key=thread_key)
    log_custom(tenant_id=tenant_id, action="thread.marked_read", metadata={"thread_key": thread_key})
    return {"status": "ok", "thread_key": thread_key}


@router.get("/rocketchat/dm-timezone")
def get_rocketchat_dm_timezone(
    room_id: str = Query(...),
    _tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> dict[str, int | None]:
    """The DM counterpart's Rocket.Chat utcOffset (see get_dm_counterpart_utc_offset),
    for the "their time" clock in the channel-transcript view. A display nicety,
    not a stored fact -- always live, never persisted, and quietly returns null
    rather than erroring when Rocket.Chat isn't configured or the lookup fails."""
    token = get_secret_value("ALLINO_ROCKETCHAT_TOKEN")
    user_id = get_secret_value("ALLINO_ROCKETCHAT_USER_ID")
    base_url = os.getenv("ALLINO_ROCKETCHAT_BASE_URL")
    if not token or not user_id or not base_url:
        return {"utc_offset_hours": None}

    offset = get_dm_counterpart_utc_offset(token=token, user_id=user_id, base_url=base_url, room_id=room_id)
    return {"utc_offset_hours": offset}


@router.get("/rocketchat/me")
def get_rocketchat_own_username(
    _tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> dict[str, str | None]:
    """The configured account's own Rocket.Chat username, so the frontend can
    highlight "your" messages in a transcript (see get_own_rocketchat_username).
    Not a secret; quietly returns null if Rocket.Chat isn't configured or the
    lookup fails, same as the dm-timezone endpoint above."""
    token = get_secret_value("ALLINO_ROCKETCHAT_TOKEN")
    user_id = get_secret_value("ALLINO_ROCKETCHAT_USER_ID")
    base_url = os.getenv("ALLINO_ROCKETCHAT_BASE_URL")
    if not token or not user_id or not base_url:
        return {"username": None}

    username = get_own_rocketchat_username(token=token, user_id=user_id, base_url=base_url)
    return {"username": username}
