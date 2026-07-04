import json
import uuid
from typing import Any

from ...core.crypto import decrypt_text, encrypt_text
from ..session import get_connection


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "source_type": row["source_type"],
        "config": json.loads(decrypt_text(row["encrypted_config"]) or "{}"),
        "poll_interval_seconds": row["poll_interval_seconds"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def upsert_builtin_connector_secret(
    *,
    tenant_id: str,
    source_type: str,
    config: dict[str, Any],
    poll_interval_seconds: int | None,
) -> dict[str, Any]:
    encrypted_config = encrypt_text(json.dumps(config))
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM builtin_connector_secrets WHERE tenant_id = ? AND source_type = ?",
            (tenant_id, source_type),
        ).fetchone()
        if existing is None:
            secret_id = uuid.uuid4().hex
            conn.execute(
                """
                INSERT INTO builtin_connector_secrets (
                    id, tenant_id, source_type, encrypted_config, poll_interval_seconds, status
                ) VALUES (?, ?, ?, ?, ?, 'active')
                """,
                (secret_id, tenant_id, source_type, encrypted_config, poll_interval_seconds),
            )
        else:
            secret_id = existing["id"]
            conn.execute(
                """
                UPDATE builtin_connector_secrets
                SET encrypted_config = ?, poll_interval_seconds = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (encrypted_config, poll_interval_seconds, secret_id),
            )
        conn.commit()

    return get_builtin_connector_secret(tenant_id=tenant_id, source_type=source_type)  # type: ignore[return-value]


def get_builtin_connector_secret(*, tenant_id: str, source_type: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, tenant_id, source_type, encrypted_config, poll_interval_seconds, status,
                   created_at, updated_at
            FROM builtin_connector_secrets
            WHERE tenant_id = ? AND source_type = ?
            """,
            (tenant_id, source_type),
        ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def list_builtin_connector_secrets(*, tenant_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, tenant_id, source_type, encrypted_config, poll_interval_seconds, status,
                   created_at, updated_at
            FROM builtin_connector_secrets
            WHERE tenant_id = ?
            ORDER BY source_type ASC
            """,
            (tenant_id,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_builtin_connector_secrets_with_polling() -> list[dict[str, Any]]:
    """Active per-tenant builtin connector secrets across all tenants that have
    poll_interval_seconds set. Used by the scheduler worker, which runs outside any
    single tenant's request context. Mirrors
    generic_connectors_repo.list_generic_connectors_with_polling() exactly."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, tenant_id, source_type, encrypted_config, poll_interval_seconds, status,
                   created_at, updated_at
            FROM builtin_connector_secrets
            WHERE status = 'active' AND poll_interval_seconds IS NOT NULL
            ORDER BY tenant_id ASC, source_type ASC
            """
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def delete_builtin_connector_secret(*, tenant_id: str, source_type: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM builtin_connector_secrets WHERE tenant_id = ? AND source_type = ?",
            (tenant_id, source_type),
        )
        conn.commit()
        return cursor.rowcount > 0
