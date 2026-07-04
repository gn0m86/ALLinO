import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from ..core.security import require_admin_mfa_permission
from ..core.tenant import resolve_tenant_id
from ..db.repositories.audit_repo import list_audit
from ..db.repositories.messages_repo import delete_all_messages
from ..services.audit import log_custom

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_AUDIT_EXPORT_LIMIT = 10000


class DeleteTenantMessagesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_tenant_id: str


@router.post("/tenant/messages/delete")
def delete_tenant_messages(
    payload: DeleteTenantMessagesRequest,
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_admin_mfa_permission),
) -> dict[str, Any]:
    if payload.confirm_tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="confirm_tenant_id does not match the current tenant")

    deleted_count = delete_all_messages(tenant_id=tenant_id)
    log_custom(
        tenant_id=tenant_id,
        action="admin.tenant_messages.deleted",
        metadata={"deleted_count": deleted_count},
    )
    return {"status": "deleted", "deleted_count": deleted_count}


@router.get("/tenant/audit/export")
def export_tenant_audit(
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_admin_mfa_permission),
) -> dict[str, Any]:
    entries = list_audit(tenant_id=tenant_id, limit=_AUDIT_EXPORT_LIMIT)
    log_custom(
        tenant_id=tenant_id,
        action="admin.tenant_audit.exported",
        metadata={"exported_count": len(entries)},
    )
    return {"tenant_id": tenant_id, "exported_count": len(entries), "entries": entries}


@router.post("/api-key/rotate")
def rotate_api_key_candidate(
    tenant_id: str = Depends(resolve_tenant_id),
    _: None = Depends(require_admin_mfa_permission),
) -> dict[str, Any]:
    """Generate a new random candidate API key. This does NOT activate it --
    ALLINO_API_KEY is read once at process startup (env var or Vault), so there
    is no live cutover here. The admin must set ALLINO_API_KEY to the returned
    value and restart the backend; the current key keeps working until then."""
    candidate_api_key = secrets.token_urlsafe(32)
    log_custom(
        tenant_id=tenant_id,
        action="admin.api_key.rotate_candidate_generated",
        metadata={},
    )
    return {
        "candidate_api_key": candidate_api_key,
        "instructions": (
            "This key is not active yet. Set ALLINO_API_KEY to this value in your "
            "environment (or Vault) and restart the backend to activate it. The "
            "current key keeps working until you do."
        ),
    }
