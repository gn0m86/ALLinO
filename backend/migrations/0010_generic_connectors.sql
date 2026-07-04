-- Generic HTTP Connector + Webhook Receiver configuration (CLAUDE.md section 5).
-- Secrets (auth token, webhook HMAC secret) are never stored here — only resolved
-- at runtime via core/secrets.py from ALLINO_GENERIC_{SLUG}_TOKEN /
-- ALLINO_GENERIC_{SLUG}_WEBHOOK_SECRET (env first, Vault fallback).

CREATE TABLE IF NOT EXISTS generic_connector_configs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    base_url TEXT,
    auth_method TEXT NOT NULL DEFAULT 'none',
    auth_header_name TEXT,
    poll_interval_seconds INTEGER,
    field_mapping TEXT NOT NULL,
    webhook_enabled INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_generic_connector_configs_tenant
ON generic_connector_configs (tenant_id);
