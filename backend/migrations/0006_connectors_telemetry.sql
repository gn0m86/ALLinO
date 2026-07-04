-- Connector registry telemetry fields for operations visibility.

ALTER TABLE connectors ADD COLUMN last_synced_at TEXT;
ALTER TABLE connectors ADD COLUMN last_error TEXT;
ALTER TABLE connectors ADD COLUMN last_processed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE connectors ADD COLUMN last_inserted INTEGER NOT NULL DEFAULT 0;
ALTER TABLE connectors ADD COLUMN last_duplicates INTEGER NOT NULL DEFAULT 0;
ALTER TABLE connectors ADD COLUMN last_rejected INTEGER NOT NULL DEFAULT 0;
ALTER TABLE connectors ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP;
