import sqlite3

import pytest

from app.db import session
from app.db.repositories.audit_repo import append_audit
from app.db.session import get_connection, init_db


def test_audit_logs_reject_update_and_delete(tmp_path) -> None:
    session.DB_PATH = tmp_path / "audit_append_only.db"
    init_db()

    append_audit(tenant_id="tenant_a", action="test.append")

    with get_connection() as conn:
        row = conn.execute("SELECT id FROM audit_logs LIMIT 1").fetchone()
        assert row is not None
        audit_id = row["id"]

        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute(
                "UPDATE audit_logs SET action = ? WHERE id = ?",
                ("test.mutated", audit_id),
            )

        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute("DELETE FROM audit_logs WHERE id = ?", (audit_id,))
