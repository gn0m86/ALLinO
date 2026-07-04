-- Additive columns for opt-in ("click to load") media attachments (Sprint 32).
-- attachment_ref is a source-specific pointer (e.g. Rocket.Chat file id), never a
-- directly-browsable URL -- the backend proxy endpoint resolves it using the
-- connector's own stored credentials, so the browser never needs (or gets) the
-- source's auth token. Both nullable; existing rows are unaffected.

ALTER TABLE messages ADD COLUMN attachment_ref TEXT;
ALTER TABLE messages ADD COLUMN attachment_type TEXT;
