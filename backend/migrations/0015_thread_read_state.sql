-- Real, server-persisted read/unread tracking for the channel-browser view
-- (Sprint 32). A thread (a chat channel/DM, keyed by messages.thread_key) is
-- "read" up to last_read_at -- any message newer than that is unread. No row
-- for a thread means "never opened" (fully unread).

CREATE TABLE IF NOT EXISTS thread_read_state (
	tenant_id TEXT NOT NULL,
	thread_key TEXT NOT NULL,
	last_read_at TEXT NOT NULL,
	PRIMARY KEY (tenant_id, thread_key)
);
