from typing import Any

from ...core.crypto import decrypt_text, encrypt_text
from ..session import get_connection


def append_connector_run(
    *,
    tenant_id: str,
    source_type: str,
    status: str,
    synced_at: str,
    processed: int = 0,
    inserted: int = 0,
    duplicates: int = 0,
    rejected: int = 0,
    error: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO connector_runs (
                tenant_id,
                source_type,
                status,
                synced_at,
                processed,
                inserted,
                duplicates,
                rejected,
                error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                source_type,
                status,
                synced_at,
                processed,
                inserted,
                duplicates,
                rejected,
                encrypt_text(error),
            ),
        )
        conn.commit()


def list_connector_runs(
    *,
    tenant_id: str,
    limit: int = 20,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if source_type:
            rows = conn.execute(
                """
                SELECT id, tenant_id, source_type, status, synced_at, processed, inserted,
                       duplicates, rejected, error, created_at
                FROM connector_runs
                WHERE tenant_id = ? AND source_type = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (tenant_id, source_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, tenant_id, source_type, status, synced_at, processed, inserted,
                       duplicates, rejected, error, created_at
                FROM connector_runs
                WHERE tenant_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "tenant_id": row["tenant_id"],
            "source_type": row["source_type"],
            "status": row["status"],
            "synced_at": row["synced_at"],
            "processed": int(row["processed"] or 0),
            "inserted": int(row["inserted"] or 0),
            "duplicates": int(row["duplicates"] or 0),
            "rejected": int(row["rejected"] or 0),
            "error": decrypt_text(row["error"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
