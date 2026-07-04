-- Per-tenant credentials for built-in named connectors (GitHub, GitLab, Jira,
-- Linear, Telegram, Slack, Discord, Zoom, Teams, Rocket.Chat, Google Calendar).
-- Unlike Generic HTTP Connectors, these sources' tokens previously only came
-- from global env vars (one credential per deployment) -- this table lets a
-- second/third tenant bring their own. encrypted_config is a Fernet-encrypted
-- JSON blob (core/crypto.py, same envelope as messages.preview) of whichever
-- fields a given source needs (token, base_url, user_id, channel_id,
-- calendar_id); never stored in plaintext when encryption-at-rest is enabled.

CREATE TABLE IF NOT EXISTS builtin_connector_secrets (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    encrypted_config TEXT NOT NULL,
    poll_interval_seconds INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, source_type)
);

CREATE INDEX IF NOT EXISTS idx_builtin_connector_secrets_tenant
ON builtin_connector_secrets (tenant_id);
