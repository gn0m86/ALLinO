from datetime import datetime, timezone

from ..session import get_connection


def mark_thread_read(tenant_id: str, thread_key: str, read_at: str | None = None) -> None:
    read_at = read_at or datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO thread_read_state (tenant_id, thread_key, last_read_at)
            VALUES (?, ?, ?)
            ON CONFLICT(tenant_id, thread_key) DO UPDATE SET
                last_read_at = excluded.last_read_at
            WHERE excluded.last_read_at > thread_read_state.last_read_at
            """,
            (tenant_id, thread_key, read_at),
        )
        conn.commit()


def get_read_state(tenant_id: str) -> dict[str, str]:
    """thread_key -> last_read_at, for every thread this tenant has ever marked read."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT thread_key, last_read_at FROM thread_read_state WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchall()
    return {row["thread_key"]: row["last_read_at"] for row in rows}
