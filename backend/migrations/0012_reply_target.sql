-- Additive column for reply targets that need more than external_id to
-- address (GitHub/GitLab: external_id is the notification id, not the
-- issue/PR itself). Nullable, unused by chat sources and by Jira/Linear
-- (their external_id is already sufficient for their comment APIs).

ALTER TABLE messages ADD COLUMN reply_target TEXT;
