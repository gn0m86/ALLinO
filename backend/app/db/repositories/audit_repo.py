import json
from typing import Any

from ...core.crypto import decrypt_text, encrypt_text
from ..session import get_connection


def append_audit(
	tenant_id: str,
	action: str,
	actor: str | None = None,
	metadata: dict[str, Any] | None = None,
) -> None:
	with get_connection() as conn:
		conn.execute(
			"""
			INSERT INTO audit_logs (tenant_id, action, actor, metadata)
			VALUES (?, ?, ?, ?)
			""",
			(
				tenant_id,
				action,
				actor,
				encrypt_text(json.dumps(metadata or {}, ensure_ascii=True)),
			),
		)
		conn.commit()


def list_audit(tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
	with get_connection() as conn:
		rows = conn.execute(
			"""
			SELECT id, tenant_id, action, actor, metadata, created_at
			FROM audit_logs
			WHERE tenant_id = ?
			ORDER BY id DESC
			LIMIT ?
			""",
			(tenant_id, limit),
		).fetchall()

	return [
		{
			"id": row["id"],
			"tenant_id": row["tenant_id"],
			"action": row["action"],
			"actor": row["actor"],
			"metadata": decrypt_text(row["metadata"]),
			"created_at": row["created_at"],
		}
		for row in rows
	]


def count_audit(tenant_id: str) -> int:
	with get_connection() as conn:
		row = conn.execute(
			"SELECT COUNT(*) AS c FROM audit_logs WHERE tenant_id = ?",
			(tenant_id,),
		).fetchone()
		return int(row["c"])
