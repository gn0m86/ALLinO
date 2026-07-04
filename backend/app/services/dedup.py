import hashlib


def dedup_key(tenant_id: str, source: str, external_id: str) -> str:
	raw = f"{tenant_id}:{source}:{external_id}"
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()
