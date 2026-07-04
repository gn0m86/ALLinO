from fastapi import Header, HTTPException, Query

from .security import get_authenticated_jwt_payload


def _payload_tenant_id(payload: dict) -> str | None:
	tenant = payload.get("tenant_id") or payload.get("tenantId") or payload.get("tid")
	if tenant is None:
		return None
	text = str(tenant).strip()
	return text or None


def resolve_tenant_id(
	tenant_id_query: str | None = Query(default=None, alias="tenant_id"),
	tenant_id_header: str | None = Header(default=None, alias="X-Tenant-Id"),
	authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
	payload = get_authenticated_jwt_payload(authorization)
	if payload is not None:
		jwt_tenant_id = _payload_tenant_id(payload)
		if not jwt_tenant_id:
			raise HTTPException(
				status_code=403,
				detail="JWT tenant claim is required (tenant_id, tenantId or tid)",
			)

		requested_tenant_id = tenant_id_header or tenant_id_query
		if requested_tenant_id and requested_tenant_id != jwt_tenant_id:
			raise HTTPException(
				status_code=403,
				detail="Requested tenant does not match authenticated JWT tenant",
			)
		return jwt_tenant_id

	tenant_id = tenant_id_header or tenant_id_query
	if not tenant_id:
		raise HTTPException(
			status_code=400,
			detail="tenant_id is required (query 'tenant_id' or header 'X-Tenant-Id')",
		)
	return tenant_id
