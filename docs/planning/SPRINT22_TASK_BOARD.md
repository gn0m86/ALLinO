# Sprint 22 — Wire Archive/Snooze (were decorative dead buttons)

Opened: 2026-07-03. Closed: 2026-07-03.

## Context

User delegated again ("продолжай" — continue). Sprint 21's board explicitly
flagged this as the next-best candidate found but not picked up: the
Archive/Snooze icon buttons in `ThreadPanel.tsx:432-440` rendered correctly
but had no `onClick` at all — pure dead UI, not even wired to a stub.
`docs/planning/PREBUILD_SPEC_V1.md:39` lists "Snooze/defer" as P1 UX scope
("если успеваем без риска"). Picked this over the other two Sprint 21
candidates (decorative Search icon needs a new backend FTS subsystem; MFA
for admin paths needs a real user decision, not autonomous pickup) because
archive/snooze is the smallest, most self-contained: one additive migration,
no new integration, no new architecture pattern (mirrors the existing reply
permission-tier and per-message-action-endpoint shape from Sprint 11/17
almost exactly).

## Scope decision

Built the literal two actions, nothing beyond:

- **Archive**: hides a message from the inbox permanently (soft-hide via
  `archived_at`, row never deleted). **No "unarchive" UI or "view archived"
  filter in this sprint** — stated explicitly as a known limitation, not
  silently cut. The data is safe and recoverable via direct DB/API access;
  a recovery UI is a separate future unit of work if it turns out to matter
  in practice.
- **Snooze**: hides a message until a fixed default duration elapses (4
  hours), then it reappears in the inbox automatically — no explicit
  "unsnooze" action needed. **No duration-picker UI** — a single click
  snoozes for the fixed default; the backend endpoint already accepts an
  optional `hours` override in its request body for future UI use, but nothing
  in this sprint's frontend calls it with a custom value. Deliberate
  simplification to avoid building a new picker/menu component for a P1 item.
- Both actions reuse the exact tenant-scoping/404/audit-logging shape
  already proven for reply (`get_message` lookup, `HTTPException(404)` if
  not found or wrong tenant, `log_custom` on every successful action) — no
  new pattern invented.

## What was built

- New migration `backend/migrations/0013_message_state.sql`: additive
  `messages.archived_at` / `messages.snoozed_until` (both nullable TEXT).
  Existing rows unaffected by construction (both columns NULL), so every
  pre-existing test kept passing with zero changes needed.
- `backend/app/domain/events.py`: `InboxMessage` gains `archived_at` /
  `snoozed_until` (`datetime | None`).
- `backend/app/db/repositories/messages_repo.py`: `_map_rows`/`get_message`
  updated for the new columns; `list_messages` gained an
  `archived_at IS NULL AND (snoozed_until IS NULL OR snoozed_until <= now)`
  filter (both cursor and non-cursor query branches) so archived/snoozed
  messages are excluded from `/inbox` and `/inbox/page` by default; new
  `archive_message(tenant_id, event_id)` / `snooze_message(tenant_id,
  event_id, snoozed_until)` functions. `count_messages` (used by `/stats`)
  deliberately left untouched -- it's a total-ingested metric, not "what's
  currently visible in the inbox"; changing its meaning wasn't needed and
  would have been a separate, unrelated decision.
- New permission tier, mirroring the existing sync/read/reply tiers exactly:
  `core/config.py` adds `ALLINO_JWT_MESSAGE_ACTIONS_ROLES` (default
  `admin,operator,analyst`) / `ALLINO_JWT_MESSAGE_ACTIONS_SCOPES` (default
  `messages:archive,messages:snooze,messages:write`); `core/security.py`
  adds `require_message_actions_permission` (API-key trusted path, JWT
  callers need the role/scope).
- New router `backend/app/api/message_actions.py`:
  `POST /api/v1/ingestion/messages/{event_id}/archive` and
  `POST /api/v1/ingestion/messages/{event_id}/snooze` (optional
  `{"hours": n}` body, `0 < hours <= 720`, default 4). Both `404` on unknown/
  wrong-tenant message, audit-log `message.archived` / `message.snoozed` on
  success. Registered in `main.py`; no CORS change needed (`POST` was
  already whitelisted).
- Frontend: `frontend/src/lib/api.ts` adds `archiveMessage()` /
  `snoozeMessage()` (mirrors `sendReply()`'s shape exactly).
  `frontend/src/components/ThreadPanel.tsx`: the two previously-dead
  `.icon-btn`s now call these, with a local pending/error state (same
  self-contained pattern as the existing `ReplyComposer`) and an inline
  error banner on failure; on success, a new `onArchived`/`onSnoozed`
  callback prop notifies the parent. `frontend/src/app/page.tsx`: one
  `handleMessageRemoved` callback (shared by both props) drops the message
  from local `items` state and clears `selected` if it was the open thread
  -- the backend inbox listing already excludes it on the next poll, this
  just makes the UI feel instant instead of waiting up to 20s for the next
  poll tick.

## Verified

- Backend: `pytest -q` => 277 passed (up from 267); `ruff check app tests
  --select F,E9` clean. New `backend/tests/test_message_actions.py` (10
  tests): 404 on unknown message (both actions), archive hides from `/inbox`
  and is audited, snooze hides with the default duration and is audited,
  custom `hours` accepted, out-of-range `hours` rejected (422), a message
  snoozed with a past timestamp (set directly via the repo function, not by
  waiting on a clock) correctly reappears in `/inbox` -- proving the active-
  filter's expiry logic without needing to manipulate wall-clock time in the
  test, tenant isolation (cross-tenant archive/snooze both `404`, unaffected
  tenant's inbox unchanged), JWT permission tier forbidden/allowed paths
  (mirrors the existing sync-permission test shape).
- Frontend: `tsc --noEmit` clean; `npm run build` success.
- **Live browser verification** (real backend + real frontend, sandboxed
  browser tool via `host.docker.internal:8000`/`:3000`): seeded 5 messages
  via the existing `/seed` endpoint, opened one, clicked Archive -- inbox
  count went 5 -> 4, the message vanished from the list, thread panel reset
  to the empty "Select a message" state, zero console errors. Opened
  another, clicked Snooze -- inbox count went 4 -> 3, same reset behavior,
  zero console errors. Cross-checked directly against the backend
  afterward: `GET /inbox` returned exactly the 3 remaining ids, `GET /audit`
  contained both `message.archived` and `message.snoozed` entries.
  Verification processes stopped via `taskkill //PID ... //F` (netstat-
  confirmed clean); `frontend/.env.local` reverted to
  `http://localhost:8000` and rebuilt; scratch DB removed.

## Explicitly out of scope (next candidates, not silently dropped)

- "View archived" filter / unarchive action (Archive is currently
  one-directional from the UI's perspective).
- Snooze duration picker (currently a fixed 4h default; the endpoint already
  accepts an override, only the UI doesn't expose one yet).
- The decorative Search icon (`page.tsx`) and MFA-for-admin-paths remain
  open from the Sprint 21 board, unchanged by this sprint.
