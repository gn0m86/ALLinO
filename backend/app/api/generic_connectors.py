import hashlib
import hmac
import json
import re
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from ..connectors.base import RetryPolicy
from ..connectors.generic_http_connector import (
    extract_items_from_payload,
    map_generic_item_to_unified_event,
    slug_to_env_key,
)
from ..core.secrets import get_secret_value
from ..core.security import require_connector_sync_permission, require_ingestion_read_permission
from ..core.tenant import resolve_tenant_id
from ..db.repositories.generic_connectors_repo import (
    create_generic_connector,
    delete_generic_connector,
    get_generic_connector,
    list_generic_connectors,
    slug_exists,
    update_generic_connector,
)
from ..services.audit import log_custom
from ..services.connector_sync import GenericConnectorSyncError, record_batch_result, sync_generic_connector

router = APIRouter(prefix="/api/v1/ingestion/connectors/generic", tags=["generic-connectors"])
webhook_router = APIRouter(tags=["webhooks"])


class GenericConnectorFieldMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    externalId: str
    timestamp: str
    preview: str | None = None
    # Locates the list of raw items nested inside a poll response or webhook body,
    # for sources whose items live deeper than a top-level array or an
    # "items"/"data"/"results" key (e.g. WhatsApp Business Cloud API's
    # "entry[].changes[].value.messages[]"). See extract_items_from_payload().
    items_path: str | None = None


class GenericConnectorCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    base_url: str | None = None
    auth_method: Literal["none", "api_key", "bearer", "basic"] = "none"
    auth_header_name: str | None = None
    poll_interval_seconds: int | None = Field(default=None, ge=30, le=86400)
    field_mapping: GenericConnectorFieldMapping
    webhook_enabled: bool = False


class GenericConnectorUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str | None = None
    auth_method: Literal["none", "api_key", "bearer", "basic"] | None = None
    auth_header_name: str | None = None
    poll_interval_seconds: int | None = Field(default=None, ge=30, le=86400)
    field_mapping: GenericConnectorFieldMapping | None = None
    webhook_enabled: bool | None = None


class GenericConnectorSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seeded_items: list[dict[str, Any]] = Field(default_factory=list)
    retry_max_attempts: int | None = Field(default=None, ge=1, le=10)
    retry_backoff_seconds: float | None = Field(default=None, ge=0.0, le=5.0)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")
    return slug or uuid4().hex[:8]


def _with_webhook_url(config: dict[str, Any]) -> dict[str, Any]:
    result = dict(config)
    result["webhook_url"] = f"/webhooks/{config['id']}" if config["webhook_enabled"] else None
    return result


@router.post("")
def create_generic_connector_config(
    payload: GenericConnectorCreateRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
) -> dict[str, Any]:
    if payload.auth_method == "api_key" and not payload.auth_header_name:
        raise HTTPException(status_code=422, detail="auth_header_name is required when auth_method is api_key")

    slug = _slugify(payload.name)
    if slug_exists(tenant_id=tenant_id, slug=slug):
        raise HTTPException(status_code=409, detail=f"A generic connector with slug '{slug}' already exists")

    config = create_generic_connector(
        config_id=uuid4().hex,
        tenant_id=tenant_id,
        name=payload.name,
        slug=slug,
        base_url=payload.base_url,
        auth_method=payload.auth_method,
        auth_header_name=payload.auth_header_name,
        poll_interval_seconds=payload.poll_interval_seconds,
        field_mapping=payload.field_mapping.model_dump(exclude_none=True),
        webhook_enabled=payload.webhook_enabled,
    )
    log_custom(
        tenant_id=tenant_id,
        action="connector.generic.created",
        metadata={"id": config["id"], "slug": slug, "webhook_enabled": payload.webhook_enabled},
    )
    return _with_webhook_url(config)


@router.get("")
def list_generic_connector_configs(
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_ingestion_read_permission),
) -> list[dict[str, Any]]:
    return [_with_webhook_url(c) for c in list_generic_connectors(tenant_id=tenant_id)]


@router.patch("/{config_id}")
def update_generic_connector_config(
    config_id: str,
    payload: GenericConnectorUpdateRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
) -> dict[str, Any]:
    existing = get_generic_connector(config_id=config_id, tenant_id=tenant_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Generic connector not found")

    updates = payload.model_dump(exclude_unset=True)

    resulting_auth_method = updates.get("auth_method", existing["auth_method"])
    resulting_header_name = updates.get("auth_header_name", existing["auth_header_name"])
    if resulting_auth_method == "api_key" and not resulting_header_name:
        raise HTTPException(status_code=422, detail="auth_header_name is required when auth_method is api_key")

    config = update_generic_connector(config_id=config_id, tenant_id=tenant_id, updates=updates)
    if config is None:
        raise HTTPException(status_code=404, detail="Generic connector not found")

    log_custom(
        tenant_id=tenant_id,
        action="connector.generic.updated",
        metadata={"id": config_id, "fields": sorted(updates.keys())},
    )
    return _with_webhook_url(config)


@router.delete("/{config_id}")
def delete_generic_connector_config(
    config_id: str,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
) -> dict[str, str]:
    deleted = delete_generic_connector(config_id=config_id, tenant_id=tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Generic connector not found")
    log_custom(tenant_id=tenant_id, action="connector.generic.deleted", metadata={"id": config_id})
    return {"status": "deleted"}


@router.post("/{config_id}/sync")
def sync_generic_connector_config(
    config_id: str,
    payload: GenericConnectorSyncRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_connector_sync_permission),
) -> dict[str, Any]:
    config = get_generic_connector(config_id=config_id, tenant_id=tenant_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Generic connector not found")

    retry_policy = RetryPolicy(
        max_attempts=payload.retry_max_attempts or RetryPolicy().max_attempts,
        backoff_seconds=(
            payload.retry_backoff_seconds
            if payload.retry_backoff_seconds is not None
            else RetryPolicy().backoff_seconds
        ),
    )
    try:
        return sync_generic_connector(
            config=config,
            tenant_id=tenant_id,
            retry_policy=retry_policy,
            seeded_items=payload.seeded_items,
        )
    except GenericConnectorSyncError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _resolve_webhook_secret(slug: str) -> str | None:
    return get_secret_value(f"ALLINO_GENERIC_{slug_to_env_key(slug)}_WEBHOOK_SECRET")


def _resolve_webhook_verify_token(slug: str) -> str | None:
    return get_secret_value(f"ALLINO_GENERIC_{slug_to_env_key(slug)}_WEBHOOK_VERIFY_TOKEN")


def _verify_signature(secret: str, body: bytes, signature_header: str | None, *, prefix: str = "sha256=") -> bool:
    if not signature_header:
        return False
    if not signature_header.startswith(prefix):
        return False
    provided = signature_header[len(prefix):].strip()
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided, expected)


def _verify_any_signature(
    secret: str,
    body: bytes,
    *,
    webhook_signature: str | None,
    hub_signature_256: str | None,
    viber_signature: str | None,
) -> bool:
    """Same HMAC-SHA256-over-raw-body check, read from whichever header the
    sender uses: our own X-Webhook-Signature, Meta Graph API's (WhatsApp
    Business Cloud API) X-Hub-Signature-256 -- both `sha256=<hex>` -- or
    Viber's X-Viber-Content-Signature, which is bare hex. The secret is the
    same per-connector ALLINO_GENERIC_{SLUG}_WEBHOOK_SECRET either way (Meta:
    the App Secret; Viber: the bot auth token)."""
    return (
        _verify_signature(secret, body, webhook_signature)
        or _verify_signature(secret, body, hub_signature_256)
        or _verify_signature(secret, body, viber_signature, prefix="")
    )


@webhook_router.get("/webhooks/{connector_id}")
def verify_webhook_subscription(
    connector_id: str,
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
) -> PlainTextResponse:
    """Meta Graph API webhook-subscription handshake (used by WhatsApp Business
    Cloud API among others): on subscribing a webhook URL, Meta issues this GET
    with a verify token and expects `hub.challenge` echoed back verbatim once the
    token matches. Opt-in per connector via ALLINO_GENERIC_{SLUG}_WEBHOOK_VERIFY_TOKEN
    — connectors that don't configure one 404, same as before this endpoint existed."""
    config = get_generic_connector(config_id=connector_id)
    if config is None or not config["webhook_enabled"]:
        raise HTTPException(status_code=404, detail="Webhook not found")

    expected_token = _resolve_webhook_verify_token(config["slug"])
    if not expected_token:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if (
        hub_mode != "subscribe"
        or hub_challenge is None
        or not hmac.compare_digest(hub_verify_token or "", expected_token)
    ):
        raise HTTPException(status_code=403, detail="Webhook verification failed")

    return PlainTextResponse(hub_challenge)


@webhook_router.post("/webhooks/{connector_id}")
async def receive_webhook_event(
    connector_id: str,
    request: Request,
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    x_viber_content_signature: str | None = Header(default=None, alias="X-Viber-Content-Signature"),
) -> dict[str, Any]:
    config = get_generic_connector(config_id=connector_id)
    if config is None or not config["webhook_enabled"]:
        raise HTTPException(status_code=404, detail="Webhook not found")

    secret = _resolve_webhook_secret(config["slug"])
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook receiver is not configured with a secret")

    body = await request.body()
    if not _verify_any_signature(
        secret,
        body,
        webhook_signature=x_webhook_signature,
        hub_signature_256=x_hub_signature_256,
        viber_signature=x_viber_content_signature,
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing webhook signature")

    try:
        payload = json.loads(body.decode("utf-8")) if body else None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    tenant_id = config["tenant_id"]
    slug = config["slug"]
    field_mapping = config["field_mapping"]
    raw_items = extract_items_from_payload(payload, field_mapping.get("items_path"))

    events: list[dict[str, Any]] = []
    for item in raw_items:
        try:
            events.append(
                map_generic_item_to_unified_event(
                    item, tenant_id=tenant_id, slug=slug, field_mapping=field_mapping
                )
            )
        except ValueError:
            continue

    try:
        result = record_batch_result(
            tenant_id=tenant_id,
            source=f"generic:{slug}",
            action_prefix=f"connector.generic.{slug}.webhook",
            events=events,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="webhook event processing failed") from exc
    return result
