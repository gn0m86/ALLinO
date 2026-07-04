from typing import Any

from ...core.crypto import decrypt_text, encrypt_text
from ..session import get_connection


def append_outbound_reply(
    *,
    tenant_id: str,
    event_id: str,
    source: str,
    external_id: str,
    text: str,
    status: str,
    error: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO outbound_replies (
                tenant_id, event_id, source, external_id, text, status, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                event_id,
                source,
                external_id,
                encrypt_text(text),
                status,
                encrypt_text(error),
            ),
        )
        conn.commit()


def list_outbound_replies(*, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, tenant_id, event_id, source, external_id, text, status, error, created_at
            FROM outbound_replies
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
            "event_id": row["event_id"],
            "source": row["source"],
            "external_id": row["external_id"],
            "text": decrypt_text(row["text"]),
            "status": row["status"],
            "error": decrypt_text(row["error"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
