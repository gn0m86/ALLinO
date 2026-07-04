-- Reply / write-back audit trail (Sprint 11). Records every outbound reply
-- attempt (sent or failed) for operational visibility and audit. The reply
-- text is encrypted at rest, consistent with messages.preview / audit_logs.metadata.

CREATE TABLE IF NOT EXISTS outbound_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    text TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outbound_replies_tenant_time
ON outbound_replies (tenant_id, created_at DESC);
