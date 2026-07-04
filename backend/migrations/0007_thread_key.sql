-- Add thread_key to messages to support stable backend-driven thread linking.
ALTER TABLE messages ADD COLUMN thread_key TEXT NOT NULL DEFAULT '';
