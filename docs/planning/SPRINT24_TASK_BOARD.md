# Sprint 24 — "View archived" + Unarchive

Opened: 2026-07-03. Closed: 2026-07-03.

## Context

User delegated again ("окей, продолжай"). Last remaining small candidate
from the Sprint 22 board: archiving a message was one-directional (no way
to see or recover an archived message from the UI, only via direct DB/API
access). Picked over the Sprint 21 Search/MFA candidates — this one needed
no new architecture decision (just an additive query param + a mirror of
the existing `archive`/`unarchive` action pair), while Search needs a real
backend FTS design decision and MFA needs a user decision on an admin
surface that doesn't exist yet.

## Scope decision

- `GET /inbox` (and `/inbox/page`) gained an `archived` query flag: when
  true, returns *only* archived messages instead of merging them into the
  normal active list — a separate view, not a mixed one, matching how
  "Archived" folders work in ordinary mail clients.
- New `POST /messages/{event_id}/unarchive` mirrors `archive` exactly
  (`404` unknown/wrong-tenant, `message.unarchived` audit entry).
- **Frontend deliberately does not add a 6th L1 nav section** — `CLAUDE.md`
  §6 fixes the shell to Inbox/Focus/Incident/Security Center/Settings.
  "Archived" is a toggle *within* the Inbox message-list column (an icon
  button next to Search, using the already-existing `ArchiveIcon`), not a
  new top-level destination.
- New `ArchivedList.tsx` is intentionally a separate, simpler component
  from `InboxList.tsx` rather than a shared/parameterized one — archived
  rows aren't selectable into a thread (no reply/archive/snooze actions
  make sense on an already-archived item beyond unarchiving it), so
  reusing `InboxList` would mean threading a bunch of archived-specific
  conditionals through a component that doesn't need them.
- **No optimistic re-insertion into the live `items` list on unarchive** —
  unlike archive/snooze (which optimistically remove, since leaving a
  now-invalid item clickable would be confusing), an unarchived message
  reappearing within the next ~20s background poll tick is fine; this
  matches the existing poll-driven freshness model used everywhere else in
  this app (e.g. connector status). Confirmed working as intended during
  live verification, not just assumed.

## What was built

- `backend/app/db/repositories/messages_repo.py`: `list_messages()` /
  `list_messages_page()` gain `archived_only: bool = False` — when true,
  the query filters `archived_at IS NOT NULL` instead of the normal
  active-only filter, and skips the `snoozed_until` comparison entirely
  (irrelevant for that branch). New `unarchive_message()`.
- `backend/app/api/ingestion.py`: `/inbox` and `/inbox/page` gain an
  `archived: bool = Query(default=False)` param threaded through.
- `backend/app/api/message_actions.py`: new `POST
  /messages/{event_id}/unarchive`, same shape as the existing `archive`/
  `snooze` endpoints (reuses `require_message_actions_permission`, no new
  permission tier needed).
- Frontend: `lib/api.ts` adds `fetchArchivedMessages()` (mirrors
  `fetchInbox()` plus the `archived=true` query param) and
  `unarchiveMessage()` (mirrors `archiveMessage()`). New
  `components/ArchivedList.tsx` — self-fetching (same convention as
  `SecurityCenter`/`GenericConnectorsPanel`), loading/error-with-retry/
  empty states per `CLAUDE.md` §6, one "Unarchive" button per row.
  `page.tsx` gets a `showArchived` toggle state, a new icon button in the
  Inbox header (`ArchiveIcon`, already existed in `Icons.tsx` but was
  unused until now), and swaps the message-list column's content for
  `<ArchivedList>` when active — the thread panel and sidebar are
  untouched, so the layout doesn't jump.

## Verified

- Backend: `pytest -q` => 280 passed (up from 277); `ruff check app tests
  --select F,E9` clean. `test_message_actions.py` extended with 3 new
  tests (archived message shows up in the archived view / disappears from
  the normal one, unknown-message unarchive is `404`, unarchive restores
  visibility and is audited) plus a tenant-isolation assertion added to the
  existing cross-tenant test.
- Frontend: `tsc --noEmit` clean; `npm run build` success.
- **Live browser verification** (real backend + real frontend, sandboxed
  browser tool via `host.docker.internal:8000`/`:3000` — this time with
  zero permission prompts for any `browser_*` tool call, since the user had
  just asked for exactly that and it was configured earlier this session):
  seeded 5 messages, archived one from its thread view, opened "View
  archived messages" — the archived item appeared with an "Unarchive"
  button, thread panel stayed on the normal "Select a message" state
  (confirming the two-panel layout wasn't disturbed). Clicked Unarchive —
  item vanished from the archived list, correctly showed the "No archived
  messages." empty state. Clicked "Back to Inbox" — inbox count read back
  as 5 (the background ~20s poll had already picked up the restored
  message by the time of the check, confirming the no-optimistic-
  reinsertion design decision above actually works in practice, not just
  in theory). Cross-checked directly against the backend: `/inbox` → 5,
  `/inbox?archived=true` → 0, audit log contained both
  `message.archived` and `message.unarchived`. Zero console errors across
  every step. Verification processes cleaned up, `.env.local` reverted,
  scratch DB removed.

## Explicitly still open

The Sprint 21 Search/MFA candidates — unchanged by this sprint. No other
new gaps surfaced.
