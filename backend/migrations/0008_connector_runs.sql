-- Historical connector sync runs for operational diagnostics.

CREATE TABLE IF NOT EXISTS connector_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    processed INTEGER NOT NULL DEFAULT 0,
    inserted INTEGER NOT NULL DEFAULT 0,
    duplicates INTEGER NOT NULL DEFAULT 0,
    rejected INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_connector_runs_tenant_time
ON connector_runs (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_connector_runs_tenant_source_time
ON connector_runs (tenant_id, source_type, created_at DESC);
