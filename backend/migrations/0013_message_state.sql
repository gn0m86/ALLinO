-- Additive columns for archive/snooze message actions (Sprint 22). Both
-- nullable; a message with neither set behaves exactly as it did before
-- this migration -- existing rows are unaffected, default inbox visibility
-- for them is unchanged.

ALTER TABLE messages ADD COLUMN archived_at TEXT;
ALTER TABLE messages ADD COLUMN snoozed_until TEXT;
