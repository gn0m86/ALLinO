-- Additive columns for the channel-browser view (Sprint 32): lets the UI group
-- chat-shaped messages into "Teams" / "Channels" / "Direct messages" sections,
-- matching how Rocket.Chat's own sidebar is organized. Both nullable -- sources
-- that don't set them (GitHub, Jira, etc.) are unaffected and simply don't
-- participate in channel-browser grouping.

ALTER TABLE messages ADD COLUMN channel_kind TEXT;
ALTER TABLE messages ADD COLUMN channel_team TEXT;
