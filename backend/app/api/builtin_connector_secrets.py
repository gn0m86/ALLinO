from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..core.security import require_connector_sync_permission, require_ingestion_read_permission
from ..core.tenant import resolve_tenant_id
from ..db.repositories.builtin_connector_secrets_repo import (
    delete_builtin_connector_secret,
    get_builtin_connector_secret,
    list_builtin_connector_secrets,
    upsert_builtin_connector_secret,
)
from ..services.audit import log_custom
from ..services.connector_sync import (
    BuiltinConnectorSecretNotConfiguredError,
    BuiltinConnectorSyncError,
    GoogleCalendarSyncError,
    sync_builtin_connector_secret,
)

router = APIRouter(prefix="/api/v1/ingestion/connectors/builtin", tags=["builtin-connector-secrets"])

BuiltinSourceType = Literal[
    "github", "gitlab", "jira", "linear", "telegram", "slack", "discord",
    "zoom", "teams", "rocketchat", "google_calendar",
]

# Extra (beyond `token`) config fields each source type accepts, and which of
# those are required rather than optional (falls back to a connector default
# or plain None otherwise). Mirrors each connector class's __init__ signature
# in app/connectors/.
_EXTRA_FIELDS: dict[str, tuple[str, ...]] = {
    "github": (),
    "gitlab": ("base_url",),
    "jira": ("base_url",),
    "linear": (),
    "telegram": (),
    "slack": ("channel_id",),
    "discord": ("channel_id",),
    "zoom": (),
    "teams": (),
    "rocketchat": ("user_id", "base_url", "channel_id"),
    "google_calendar": ("calendar_id", "client_id", "client_secret", "refresh_token"),
}
_REQUIRED_EXTRA_FIELDS: dict[str, tuple[str, ...]] = {
    "rocketchat": ("user_id", "base_url"),
}


class BuiltinConnectorSecretRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Every source except google_calendar requires this (enforced in the endpoint,
    # not here, since google_calendar can authenticate via client_id/client_secret/
    # refresh_token instead -- see refresh_google_access_token in
    # connectors/google_calendar_connector.py).
    token: str | None = Field(default=None, min_length=1)
    base_url: str | None = None
    user_id: str | None = None
    channel_id: str | None = None
    calendar_id: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    poll_interval_seconds: int | None = Field(default=None, ge=30, le=86400)


def _public_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": row["source_type"],
        "configured": True,
        "poll_interval_seconds": row["poll_interval_seconds"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.post("/{source_type}/secret")
def upsert_builtin_connector_secret_endpoint(
    source_type: BuiltinSourceType,
    payload: BuiltinConnectorSecretRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
) -> dict[str, Any]:
    allowed_extra = _EXTRA_FIELDS[source_type]
    required_extra = _REQUIRED_EXTRA_FIELDS.get(source_type, ())
    for field in required_extra:
        if not getattr(payload, field):
            raise HTTPException(status_code=422, detail=f"{field} is required for source_type '{source_type}'")

    has_oauth_refresh = bool(payload.client_id and payload.client_secret and payload.refresh_token)
    if source_type == "google_calendar":
        if not payload.token and not has_oauth_refresh:
            raise HTTPException(
                status_code=422,
                detail="google_calendar requires either token, or client_id + client_secret + refresh_token",
            )
    elif not payload.token:
        raise HTTPException(status_code=422, detail=f"token is required for source_type '{source_type}'")

    config: dict[str, Any] = {}
    if payload.token:
        config["token"] = payload.token
    for field in allowed_extra:
        value = getattr(payload, field)
        if value:
            config[field] = value

    row = upsert_builtin_connector_secret(
        tenant_id=tenant_id,
        source_type=source_type,
        config=config,
        poll_interval_seconds=payload.poll_interval_seconds,
    )
    log_custom(
        tenant_id=tenant_id,
        action="connector.builtin.secret.upserted",
        metadata={"source_type": source_type, "poll_interval_seconds": payload.poll_interval_seconds},
    )
    return _public_view(row)


@router.post("/{source_type}/sync")
def sync_builtin_connector_secret_endpoint(
    source_type: BuiltinSourceType,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
) -> dict[str, Any]:
    try:
        return sync_builtin_connector_secret(tenant_id=tenant_id, source_type=source_type)
    except BuiltinConnectorSecretNotConfiguredError as exc:
        raise HTTPException(status_code=404, detail="No credentials configured for this source") from exc
    except (BuiltinConnectorSyncError, GoogleCalendarSyncError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/secrets")
def list_builtin_connector_secrets_endpoint(
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[dict[str, Any]]:
    return [_public_view(row) for row in list_builtin_connector_secrets(tenant_id=tenant_id)]


@router.delete("/{source_type}/secret")
def delete_builtin_connector_secret_endpoint(
    source_type: BuiltinSourceType,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
) -> dict[str, str]:
    existing = get_builtin_connector_secret(tenant_id=tenant_id, source_type=source_type)
    if existing is None:
        raise HTTPException(status_code=404, detail="Builtin connector secret not configured")
    delete_builtin_connector_secret(tenant_id=tenant_id, source_type=source_type)
    log_custom(
        tenant_id=tenant_id,
        action="connector.builtin.secret.deleted",
        metadata={"source_type": source_type},
    )
    return {"status": "deleted"}
