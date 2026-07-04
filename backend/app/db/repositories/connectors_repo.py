from typing import Any

from ...core.crypto import decrypt_text, encrypt_text
from ..session import get_connection


def upsert_connector_status(
    tenant_id: str,
    source_type: str,
    status: str,
    *,
    last_synced_at: str | None = None,
    last_error: str | None = None,
    last_processed: int = 0,
    last_inserted: int = 0,
    last_duplicates: int = 0,
    last_rejected: int = 0,
) -> None:
    connector_id = f"{tenant_id}:{source_type}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO connectors (
                id,
                tenant_id,
                source_type,
                status,
                last_synced_at,
                last_error,
                last_processed,
                last_inserted,
                last_duplicates,
                last_rejected,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                last_synced_at = excluded.last_synced_at,
                last_error = excluded.last_error,
                last_processed = excluded.last_processed,
                last_inserted = excluded.last_inserted,
                last_duplicates = excluded.last_duplicates,
                last_rejected = excluded.last_rejected,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                connector_id,
                tenant_id,
                source_type,
                status,
                last_synced_at,
                encrypt_text(last_error),
                last_processed,
                last_inserted,
                last_duplicates,
                last_rejected,
            ),
        )
        conn.commit()


def get_connector(connector_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                id,
                tenant_id,
                source_type,
                status,
                created_at,
                updated_at,
                last_synced_at,
                last_error,
                last_processed,
                last_inserted,
                last_duplicates,
                last_rejected
            FROM connectors
            WHERE id = ?
            """,
            (connector_id,),
        ).fetchone()

    if row is None:
        return None
    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "source_type": row["source_type"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_synced_at": row["last_synced_at"],
        "last_error": decrypt_text(row["last_error"]),
        "last_processed": int(row["last_processed"] or 0),
        "last_inserted": int(row["last_inserted"] or 0),
        "last_duplicates": int(row["last_duplicates"] or 0),
        "last_rejected": int(row["last_rejected"] or 0),
    }


def list_connectors(tenant_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                tenant_id,
                source_type,
                status,
                created_at,
                updated_at,
                last_synced_at,
                last_error,
                last_processed,
                last_inserted,
                last_duplicates,
                last_rejected
            FROM connectors
            WHERE tenant_id = ?
            ORDER BY source_type ASC
            """,
            (tenant_id,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "tenant_id": row["tenant_id"],
            "source_type": row["source_type"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_synced_at": row["last_synced_at"],
            "last_error": decrypt_text(row["last_error"]),
            "last_processed": int(row["last_processed"] or 0),
            "last_inserted": int(row["last_inserted"] or 0),
            "last_duplicates": int(row["last_duplicates"] or 0),
            "last_rejected": int(row["last_rejected"] or 0),
        }
        for row in rows
    ]
