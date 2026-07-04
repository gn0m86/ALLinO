import os

from .secrets import get_secret_value

# If set, all ingestion endpoints require the matching X-API-Key header.
# Leave unset only for explicitly allowed local dev mode.
ALLINO_API_KEY: str | None = get_secret_value("ALLINO_API_KEY")

# Optional JWT auth settings. If ALLINO_JWT_SECRET (symmetric, HS*) or
# ALLINO_JWT_PUBLIC_KEY (asymmetric, RS*/ES*/PS*) is set, Bearer tokens are
# accepted in the Authorization header. This service only ever verifies JWTs
# issued by an external IdP — it never issues them — so only a public key is
# needed for the asymmetric case, never a private key.
ALLINO_JWT_SECRET: str | None = get_secret_value("ALLINO_JWT_SECRET")
ALLINO_JWT_PUBLIC_KEY: str | None = get_secret_value("ALLINO_JWT_PUBLIC_KEY")
ALLINO_JWT_ALGORITHM: str = os.getenv("ALLINO_JWT_ALGORITHM", "HS256").strip() or "HS256"
ALLINO_JWT_ISSUER: str | None = os.getenv("ALLINO_JWT_ISSUER") or None
ALLINO_JWT_AUDIENCE: str | None = os.getenv("ALLINO_JWT_AUDIENCE") or None
ALLINO_JWT_SYNC_ROLES: set[str] = {
	r.strip().lower()
	for r in os.getenv("ALLINO_JWT_SYNC_ROLES", "admin,operator").split(",")
	if r.strip()
}
ALLINO_JWT_SYNC_SCOPES: set[str] = {
	s.strip().lower()
	for s in os.getenv("ALLINO_JWT_SYNC_SCOPES", "connectors:sync,sync:connectors").split(",")
	if s.strip()
}
ALLINO_JWT_READ_ROLES: set[str] = {
	r.strip().lower()
	for r in os.getenv("ALLINO_JWT_READ_ROLES", "admin,operator,analyst,viewer").split(",")
	if r.strip()
}
ALLINO_JWT_READ_SCOPES: set[str] = {
	s.strip().lower()
	for s in os.getenv(
		"ALLINO_JWT_READ_SCOPES",
		"ingestion:read,inbox:read,audit:read,metrics:read,connectors:read",
	).split(",")
	if s.strip()
}
ALLINO_JWT_REPLY_ROLES: set[str] = {
	r.strip().lower()
	for r in os.getenv("ALLINO_JWT_REPLY_ROLES", "admin,operator").split(",")
	if r.strip()
}
ALLINO_JWT_REPLY_SCOPES: set[str] = {
	s.strip().lower()
	for s in os.getenv("ALLINO_JWT_REPLY_SCOPES", "messages:reply,reply:send").split(",")
	if s.strip()
}
ALLINO_JWT_MESSAGE_ACTIONS_ROLES: set[str] = {
	r.strip().lower()
	for r in os.getenv("ALLINO_JWT_MESSAGE_ACTIONS_ROLES", "admin,operator,analyst").split(",")
	if r.strip()
}
ALLINO_JWT_MESSAGE_ACTIONS_SCOPES: set[str] = {
	s.strip().lower()
	for s in os.getenv(
		"ALLINO_JWT_MESSAGE_ACTIONS_SCOPES",
		"messages:archive,messages:snooze,messages:write",
	).split(",")
	if s.strip()
}
# Admin tier: narrower than the other tiers (admin only, not
# operator/analyst/viewer) since it gates destructive actions. Unlike every
# other tier, holding this role/scope (or the API key) is NOT sufficient by
# itself -- see require_admin_mfa_permission in core/security.py, which also
# requires a valid TOTP code regardless of auth method.
ALLINO_JWT_ADMIN_ROLES: set[str] = {
	r.strip().lower()
	for r in os.getenv("ALLINO_JWT_ADMIN_ROLES", "admin").split(",")
	if r.strip()
}
ALLINO_JWT_ADMIN_SCOPES: set[str] = {
	s.strip().lower()
	for s in os.getenv("ALLINO_JWT_ADMIN_SCOPES", "admin:destructive,tenant:delete").split(",")
	if s.strip()
}

# Runtime environment marker used by security policy.
# Expected values: development, test, staging, production.
ALLINO_ENV: str = os.getenv("ALLINO_ENV", "development").strip().lower()

# Allow unauthenticated ingestion only in local development when API key is absent.
# Set to false to force API key checks even in development.
ALLINO_ALLOW_INSECURE_DEV: bool = (
	os.getenv("ALLINO_ALLOW_INSECURE_DEV", "false").strip().lower() in {"1", "true", "yes", "on"}
)

ALLINO_ALLOWED_ORIGINS: str = os.getenv("ALLINO_ALLOWED_ORIGINS", "http://localhost:3000")

# Feature-flagged event bus start path (Redis Streams).
ALLINO_EVENT_BUS_ENABLED: bool = (
	os.getenv("ALLINO_EVENT_BUS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
)
ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED: bool = (
	os.getenv("ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED", "false").strip().lower()
	in {"1", "true", "yes", "on"}
)
ALLINO_EVENT_BUS_ASYNC_TIMEOUT_SECONDS: float = float(
	os.getenv("ALLINO_EVENT_BUS_ASYNC_TIMEOUT_SECONDS", "5")
)
ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS: int = int(
	os.getenv("ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS", "3")
)
ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED: bool = (
	os.getenv("ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED", "false").strip().lower()
	in {"1", "true", "yes", "on"}
)
ALLINO_EVENT_BUS_EXTERNAL_WORKER_TIMEOUT_SECONDS: float = float(
	os.getenv("ALLINO_EVENT_BUS_EXTERNAL_WORKER_TIMEOUT_SECONDS", "5")
)
ALLINO_EVENT_BUS_EXTERNAL_WORKER_MAX_ATTEMPTS: int = int(
	os.getenv("ALLINO_EVENT_BUS_EXTERNAL_WORKER_MAX_ATTEMPTS", "3")
)
ALLINO_EVENT_BUS_EXTERNAL_WORKER_BACKOFF_SECONDS: float = float(
	os.getenv("ALLINO_EVENT_BUS_EXTERNAL_WORKER_BACKOFF_SECONDS", "0.2")
)
ALLINO_EVENT_BUS_EXTERNAL_WORKER_DLQ_STREAM: str = os.getenv(
	"ALLINO_EVENT_BUS_EXTERNAL_WORKER_DLQ_STREAM",
	"allino:ingestion:dlq",
)
ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX: str | None = (
	os.getenv("ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX") or None
)
ALLINO_REDIS_URL: str = os.getenv("ALLINO_REDIS_URL", "redis://localhost:6379/0")
ALLINO_REDIS_STREAM_PREFIX: str = os.getenv("ALLINO_REDIS_STREAM_PREFIX", "allino:ingestion")

# Scheduler worker: in-process cadence for checking which generic connectors are due
# for a poll (per-connector poll_interval_seconds, not the worker's own tick rate).
ALLINO_SCHEDULER_WORKER_POLL_INTERVAL_SECONDS: float = float(
	os.getenv("ALLINO_SCHEDULER_WORKER_POLL_INTERVAL_SECONDS", "30")
)

# Optional Google Calendar auto-polling (built-in connectors have no persisted
# per-tenant config table like Generic HTTP Connectors do, so this is env-scoped to
# a single tenant/calendar rather than a DB-driven list -- see Sprint 19 board).
ALLINO_GOOGLE_CALENDAR_POLL_ENABLED: bool = (
	os.getenv("ALLINO_GOOGLE_CALENDAR_POLL_ENABLED", "false").strip().lower()
	in {"1", "true", "yes", "on"}
)
ALLINO_GOOGLE_CALENDAR_POLL_INTERVAL_SECONDS: float = float(
	os.getenv("ALLINO_GOOGLE_CALENDAR_POLL_INTERVAL_SECONDS", "900")
)
ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID: str | None = (
	os.getenv("ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID") or None
)
ALLINO_GOOGLE_CALENDAR_POLL_CALENDAR_ID: str = os.getenv(
	"ALLINO_GOOGLE_CALENDAR_POLL_CALENDAR_ID", "primary"
)

# Optional auto-polling for the other built-in named connectors (GitHub, GitLab,
# Jira, Linear, Telegram, Slack, Discord, Zoom, Teams, Rocket.Chat). Same
# env-scoped-to-a-single-tenant shape as Google Calendar polling above -- none of
# these have a persisted per-tenant config table, so this is not multi-tenant.
# A connector is only attempted if its required secret is actually configured.
ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED: bool = (
	os.getenv("ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED", "false").strip().lower()
	in {"1", "true", "yes", "on"}
)
ALLINO_BUILTIN_CONNECTORS_POLL_INTERVAL_SECONDS: float = float(
	os.getenv("ALLINO_BUILTIN_CONNECTORS_POLL_INTERVAL_SECONDS", "300")
)
ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID: str | None = (
	os.getenv("ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID") or None
)

# In-memory rate limiting for ingestion/auth path.
ALLINO_RATE_LIMIT_ENABLED: bool = (
	os.getenv("ALLINO_RATE_LIMIT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
)
ALLINO_RATE_LIMIT_REQUESTS: int = int(os.getenv("ALLINO_RATE_LIMIT_REQUESTS", "120"))
ALLINO_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("ALLINO_RATE_LIMIT_WINDOW_SECONDS", "60"))

# HTTP security headers.
ALLINO_SECURITY_HEADERS_ENABLED: bool = (
	os.getenv("ALLINO_SECURITY_HEADERS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
)
ALLINO_CSP_POLICY: str = os.getenv(
	"ALLINO_CSP_POLICY",
	"default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
)
ALLINO_HSTS_ENABLED: bool = (
	os.getenv("ALLINO_HSTS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
)
ALLINO_HSTS_MAX_AGE: int = int(os.getenv("ALLINO_HSTS_MAX_AGE", "31536000"))
ALLINO_HSTS_INCLUDE_SUBDOMAINS: bool = (
	os.getenv("ALLINO_HSTS_INCLUDE_SUBDOMAINS", "true").strip().lower() in {"1", "true", "yes", "on"}
)
ALLINO_HSTS_PRELOAD: bool = (
	os.getenv("ALLINO_HSTS_PRELOAD", "false").strip().lower() in {"1", "true", "yes", "on"}
)

# Field-level encryption at rest for sensitive persisted strings.
ALLINO_ENCRYPTION_AT_REST_ENABLED: bool = (
	os.getenv("ALLINO_ENCRYPTION_AT_REST_ENABLED", "true").strip().lower()
	in {"1", "true", "yes", "on"}
)
ALLINO_ENCRYPTION_KEY: str | None = get_secret_value("ALLINO_ENCRYPTION_KEY")
