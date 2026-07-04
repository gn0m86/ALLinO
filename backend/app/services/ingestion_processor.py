from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..db.repositories.messages_repo import add_if_new
from ..domain.events import UnifiedEvent
from .audit import log_custom, log_ingestion_event
from .dedup import dedup_key
from .normalizer import normalize_event

_SECRET_KEYS = {"token", "access_token", "api_key", "authorization", "password", "secret"}


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for k, v in value.items():
            if k.lower() in _SECRET_KEYS:
                sanitized[k] = "***"
            else:
                sanitized[k] = redact_secrets(v)
        return sanitized
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def process_connector_batch(
    *,
    events: list[dict[str, Any]],
    tenant_id: str,
    action_prefix: str,
) -> dict[str, int | float]:
    processed = inserted = duplicates = rejected = 0
    total_lag_ms = 0.0
    lag_samples = 0
    now = datetime.now(timezone.utc)

    for raw_event in events:
        processed += 1
        try:
            event = UnifiedEvent(**raw_event)
        except Exception:
            rejected += 1
            log_custom(
                tenant_id=tenant_id,
                action=f"{action_prefix}.rejected",
                metadata={"raw_event": redact_secrets(raw_event)},
            )
            continue

        if event.tenantId != tenant_id:
            rejected += 1
            log_custom(
                tenant_id=tenant_id,
                action=f"{action_prefix}.tenant_mismatch",
                metadata={"event_tenant": event.tenantId, "auth_tenant": tenant_id},
            )
            continue

        ts = event.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        total_lag_ms += (now - ts).total_seconds() * 1000
        lag_samples += 1

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
            action=f"{action_prefix}.event",
            event_id=event.eventId,
            source=event.sourceType,
            external_id=event.externalId,
            status=status,
        )

    return {
        "processed": processed,
        "inserted": inserted,
        "duplicates": duplicates,
        "rejected": rejected,
        "total_lag_ms": total_lag_ms,
        "lag_samples": lag_samples,
    }
