CREATE TABLE IF NOT EXISTS users (
	id TEXT PRIMARY KEY,
	tenant_id TEXT NOT NULL,
	email TEXT,
	role TEXT,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS connectors (
	id TEXT PRIMARY KEY,
	tenant_id TEXT NOT NULL,
	source_type TEXT NOT NULL,
	status TEXT NOT NULL DEFAULT 'active',
	created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS threads (
	id TEXT PRIMARY KEY,
	tenant_id TEXT NOT NULL,
	connector_id TEXT,
	external_thread_id TEXT,
	subject TEXT,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	dedup_hash TEXT NOT NULL UNIQUE,
	event_id TEXT NOT NULL,
	tenant_id TEXT NOT NULL,
	source TEXT NOT NULL,
	external_id TEXT NOT NULL,
	timestamp TEXT NOT NULL,
	preview TEXT,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_tenant_time
ON messages (tenant_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	tenant_id TEXT NOT NULL,
	action TEXT NOT NULL,
	actor TEXT,
	metadata TEXT,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
