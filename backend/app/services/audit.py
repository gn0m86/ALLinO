from typing import Any

from ..db.repositories.audit_repo import append_audit


def log_ingestion_event(
	tenant_id: str,
	action: str,
	event_id: str,
	source: str,
	external_id: str,
	status: str,
) -> None:
	append_audit(
		tenant_id=tenant_id,
		action=action,
		actor="system",
		metadata={
			"event_id": event_id,
			"source": source,
			"external_id": external_id,
			"status": status,
		},
	)


def log_custom(
	tenant_id: str,
	action: str,
	metadata: dict[str, Any] | None = None,
) -> None:
	append_audit(
		tenant_id=tenant_id,
		action=action,
		actor="system",
		metadata=metadata,
	)
