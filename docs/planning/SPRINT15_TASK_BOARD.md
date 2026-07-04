# Sprint 15 Task Board

Opened: 2026-07-02

## Scope decision

Continuing under the user's standing "continue what you can without me"
delegation. Reviewed the known-gaps list from `CURRENT_STATE.md` §6:

- WhatsApp Business / Viber (Wave 3 remainder): **not started this sprint**.
  Both are fundamentally webhook-push APIs with no message-list/poll
  endpoint (unlike Rocket.Chat, which has a real REST `channels.messages`
  list). Building either would mean a *new* connector shape — a built-in
  webhook receiver with provider-specific handshake/signature verification
  (WhatsApp's `hub.challenge` GET verification + `X-Hub-Signature-256`;
  Viber's own callback verification) — distinct from every connector this
  codebase has today and distinct from the Generic HTTP Connector's webhook
  receiver too (that one is intentionally provider-agnostic). That is an
  architecture decision, not a same-shape connector addition, so it is left
  for a dedicated sprint rather than forced into this one.
- Google Calendar push/watch-channel: **not started**. Needs new scheduler
  infrastructure this project doesn't have for any connector — same
  reasoning as every prior sprint that touched this gap.
- Generic HTTP Connector edit (PATCH): small and safe, but lower value than
  the item below; left for a follow-up sprint if there's room.
- **Picked for this sprint: extend reply/write-back to Discord and
  Rocket.Chat.** Sprint 11 scoped reply to Telegram+Slack only "for MVP,"
  not because other sources were incompatible — it explicitly named
  GitHub/GitLab/Jira/Linear as a different data model (issue/PR comments)
  and Google Calendar as having no reply semantics at all, but said nothing
  ruling out Discord/Rocket.Chat, which are chat-message-shaped exactly like
  Telegram/Slack: both already encode `channel:message_id` in `external_id`
  (needed nothing new there), and both have a plain bot-token message-post
  API with no OAuth flow, the same shape Sprint 11 relied on. This is a
  same-pattern extension of an existing feature, not a new architecture —
  the safest kind of "continue without me" work.

## S15-01: Reply support for Discord and Rocket.Chat

Status: closed

- `backend/app/connectors/discord_connector.py` adds `send_discord_reply()`
  (Discord REST `POST /channels/{channel_id}/messages` with `Bot {token}`
  auth, sets `message_reference.message_id` to reply in-context when the
  external_id's message-id segment is present).
- `backend/app/connectors/rocketchat_connector.py` adds
  `send_rocketchat_reply()` (Rocket.Chat REST `POST /api/v1/chat.postMessage`
  with `X-Auth-Token`/`X-User-Id` headers). Unlike every other reply sender,
  this one needs 2 extra pieces of config beyond the token
  (`ALLINO_ROCKETCHAT_USER_ID`, `ALLINO_ROCKETCHAT_BASE_URL`, self-hosted so
  no fixed API host) — resolved the same way the connector itself resolves
  them, and checked for presence in `replies.py`'s pre-flight config check
  before attempting delivery (fail-closed 503, not a spurious 502 delivery
  failure, for pure misconfiguration).
- `backend/app/api/replies.py`: `_REPLY_TOKEN_ENV_KEYS` and `_REPLY_SENDERS`
  extended with `discord`/`rocketchat` entries; new
  `_REPLY_EXTRA_CONFIG_ENV_KEYS` dict (currently only `rocketchat`) checked
  alongside the token before the existing fail-closed-503 branch.
- `frontend/src/lib/types.ts`: `REPLY_SUPPORTED_SOURCES` extended to
  `["telegram", "slack", "discord", "rocketchat"]`. No other frontend change
  needed — `ThreadPanel.tsx`'s composer already keys off this constant.
- Tests: `backend/tests/test_reply_delivery.py` extended with
  `send_discord_reply`/`send_rocketchat_reply` unit tests (request shape,
  missing-channel ValueError, API-error RuntimeError — same shape as the
  existing Telegram/Slack tests). `backend/tests/test_reply_endpoint.py`
  extended with a Rocket.Chat-specific 503 case covering the new
  extra-config check (token present, user_id/base_url missing).

- Verified: backend `pytest -q` => 222 passed (up from 213);
  `ruff check app tests --select F,E9` => all checks passed. Frontend:
  `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification (per `CLAUDE.md` §6, mandatory): seeded one
  Discord message and one Rocket.Chat message via their sync endpoints
  against a real running backend, confirmed in a real browser that: the
  reply composer now renders for both sources (previously showed "Replies
  aren't supported"), typing and sending a reply on each correctly hits
  `POST /messages/{event_id}/reply`, and — since no
  `ALLINO_DISCORD_BOT_TOKEN`/`ALLINO_ROCKETCHAT_TOKEN` were configured in
  this verification run — both correctly surface the fail-closed 503 "Reply
  is not configured for source '...'" message (same intentional pattern as
  the Sprint 11 Telegram verification; the Rocket.Chat case additionally
  exercises the new extra-config check, since its token env var could be set
  without `ALLINO_ROCKETCHAT_USER_ID`/`..._BASE_URL` and still correctly
  fail closed rather than attempt delivery). The two console errors seen
  were exactly these two expected 503s, nothing else. Frontend rebuilt
  afterward without the sandbox-only backend URL override.

## Explicitly out of scope for this sprint

- WhatsApp Business, Viber (see reasoning above — different transport shape,
  needs its own architecture decision).
- Google Calendar push/watch-channel renewal (needs scheduler infra).
- Reply for GitHub/GitLab/Jira/Linear/Zoom/Teams — issue/PR-comment or
  meeting-shaped data models, not chat replies; Google Calendar has no
  reply semantics at all. Same reasoning Sprint 11 already established.
- Generic HTTP Connector edit (PATCH) — left for a follow-up sprint.
