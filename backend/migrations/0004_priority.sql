-- Add priority column to messages for rule-based classifier (S2-06).
-- DEFAULT 'normal' ensures existing rows stay consistent without a backfill.
ALTER TABLE messages ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal';
