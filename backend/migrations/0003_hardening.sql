-- Migration tracking: record which migrations have been applied.
-- This table is also bootstrapped in code (db/session.py) so it always exists before any migration runs.
CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Audit log performance: full-table scan on every /audit call without this index.
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_time
ON audit_logs (tenant_id, created_at DESC);
