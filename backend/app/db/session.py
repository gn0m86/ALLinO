import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("ALLINO_DB_PATH", str(BASE_DIR / "data" / "allino.db")))
MIGRATIONS_DIR = BASE_DIR / "migrations"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        return

    with get_connection() as conn:
        # Bootstrap the migrations tracking table before anything else.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        rows = conn.execute("SELECT name FROM schema_migrations").fetchall()
        applied = {row[0] for row in rows}

    for migration_file in migration_files:
        if migration_file.name in applied:
            continue
        sql = migration_file.read_text(encoding="utf-8").strip()
        if sql:
            with get_connection() as conn:
                conn.executescript(sql)
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)",
                    (migration_file.name,),
                )
                conn.commit()
