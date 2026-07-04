from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..core.security import require_message_actions_permission
from ..core.tenant import resolve_tenant_id
from ..db.repositories.messages_repo import archive_message, get_message, snooze_message, unarchive_message
from ..services.audit import log_custom

router = APIRouter(prefix="/api/v1/ingestion", tags=["message-actions"])

# Single fixed default duration, not a duration picker -- matches the
# smallest-useful-thing scope of this feature (see Sprint 22 board). Callers
# may still override via the request body.
DEFAULT_SNOOZE_HOURS = 4.0
MAX_SNOOZE_HOURS = 24.0 * 30  # 30 days, sanity bound


class SnoozeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: float = Field(default=DEFAULT_SNOOZE_HOURS, gt=0, le=MAX_SNOOZE_HOURS)


@router.post("/messages/{event_id}/archive")
def archive_message_endpoint(
    event_id: str,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_message_actions_permission),
) -> dict[str, Any]:
    message = get_message(tenant_id=tenant_id, event_id=event_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    archive_message(tenant_id=tenant_id, event_id=event_id)
    log_custom(
        tenant_id=tenant_id,
        action="message.archived",
        metadata={"event_id": event_id, "source": message.source},
    )
    return {"status": "archived", "event_id": event_id}


@router.post("/messages/{event_id}/unarchive")
def unarchive_message_endpoint(
    event_id: str,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_message_actions_permission),
) -> dict[str, Any]:
    message = get_message(tenant_id=tenant_id, event_id=event_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    unarchive_message(tenant_id=tenant_id, event_id=event_id)
    log_custom(
        tenant_id=tenant_id,
        action="message.unarchived",
        metadata={"event_id": event_id, "source": message.source},
    )
    return {"status": "active", "event_id": event_id}


@router.post("/messages/{event_id}/snooze")
def snooze_message_endpoint(
    event_id: str,
    payload: SnoozeRequest | None = None,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_message_actions_permission),
) -> dict[str, Any]:
    message = get_message(tenant_id=tenant_id, event_id=event_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    hours = payload.hours if payload is not None else DEFAULT_SNOOZE_HOURS
    until = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    snooze_message(tenant_id=tenant_id, event_id=event_id, snoozed_until=until)
    log_custom(
        tenant_id=tenant_id,
        action="message.snoozed",
        metadata={"event_id": event_id, "source": message.source, "snoozed_until": until},
    )
    return {"status": "snoozed", "event_id": event_id, "snoozed_until": until}
