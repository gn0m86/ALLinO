# Sprint 25 — Inbox search (exact match)

Opened: 2026-07-03. Closed: 2026-07-03.

## Context

User was asked to decide between exact-match and fuzzy search (Sprint 21
flagged Search as decorative dead UI needing a real design decision). User
chose exact match, described as "полноценный поиск" (a proper/full search,
not a stub) even though it takes more work than a trivial one. This closes
the last remaining Sprint 21 candidate that was actually greenlit this
session — MFA-for-admin-paths was discussed (explained with concrete
examples) but the user didn't request building it; still open, no board.

## A security tradeoff surfaced and resolved without asking (conservative default)

`messages.preview` is encrypted at rest (`CLAUDE.md` §4 security gate,
implemented in an earlier sprint). A conventional full-text search
implementation (SQLite FTS5 virtual table) needs plaintext tokens to index
— building one would mean storing a second, searchable plaintext copy of
message content, which is a real regression of the encryption-at-rest
guarantee. This wasn't the user's call to make blind (they asked for
"exact match search," not "weaken the encryption-at-rest guarantee") --
resolving it required picking the conservative interpretation, not
surfacing a false binary.

**What was built instead:** `search_messages()` fetches a bounded,
recency-ordered window of the tenant's *active* messages (existing
`_ACTIVE_FILTER`, same one `/inbox` already uses), decrypts them through
the same `_map_rows()` path every other read already uses (no new plaintext
persisted anywhere), and matches in Python via case-insensitive substring
matching against `preview`/`external_id`/`source`. This is "exact match"
in the sense the user asked for (no fuzzy/typo-tolerant/stemmed matching)
while keeping the encryption-at-rest guarantee fully intact — zero new
persisted plaintext.

**Documented scale limit, not silently hidden:** the scan window is capped
at `_SEARCH_SCAN_LIMIT = 5000` messages (a constant with an explanatory
comment in `messages_repo.py`). Fine at the local-first, single-tenant
scale this project targets. If a tenant's active-message volume ever
exceeds that, *that's* the trigger to revisit — and revisiting means having
the FTS-vs-encryption conversation with the user explicitly, not defaulting
into it.

## Other scope decisions

- Search only covers **active** messages (same default as `/inbox` —
  excludes archived and currently-snoozed). Searching archived messages is
  explicitly out of scope; can be added later (`archived_only`-style flag
  already exists on the underlying query shape) if it turns out to matter.
- Reused `InboxList` to render results (selecting a result behaves exactly
  like selecting a normal inbox item — opens the thread, supports
  reply/archive/snooze) instead of building a second list renderer.
- Debounced (300ms) client-side, matching how a search-as-you-type field is
  conventionally built; no "press Enter to search" step.

## What was built

- `backend/app/db/repositories/messages_repo.py`: `search_messages(tenant_id,
  query, limit=50)`.
- `backend/app/api/ingestion.py`: `GET /api/v1/ingestion/search?q=...`
  (tenant-scoped, reuses `require_ingestion_read_permission` — same tier as
  `/inbox`, no new permission surface).
- Frontend: `lib/api.ts` adds `searchMessages()`. New
  `components/SearchPanel.tsx` — self-contained (owns its own query/
  results/loading/error state), debounced fetch, loading/empty/
  no-results/error states per `CLAUDE.md` §6, results rendered via the
  existing `InboxList`. `page.tsx` gets a `searchOpen` toggle: the
  previously-decorative Search icon button now opens this panel in place of
  the message-list column's normal content (same swap pattern as the
  Sprint 24 Archived toggle); selecting a result closes search and opens
  the thread, same as a normal inbox click.

## Verified

- Backend: `pytest -q` => 288 passed (up from 280); `ruff check app tests
  --select F,E9` clean. New `backend/tests/test_search.py` (8 tests):
  matches preview text, matches external_id, case-insensitive, no-match
  returns empty list, archived messages excluded from results, tenant
  isolation, `limit` respected, empty query rejected (422).
- Frontend: `tsc --noEmit` clean; `npm run build` success.
- **Live browser verification** (real backend + real frontend, sandboxed
  browser tool, zero permission prompts): seeded two messages with
  deliberately distinct preview text ("database migration failed on
  staging" vs "deploy succeeded without issues"). Opened Search, typed
  "migration" — only the matching message appeared in results (confirmed
  the other was correctly excluded, not just that a match appeared).
  Clicked the result — search closed, the correct message opened in the
  thread panel with reply/archive/snooze all functional (a real inbox
  item, not a dead-end preview). Reopened search, typed a guaranteed-no-
  match string — got the "No matches" empty state, not an error or a
  stale result list. Zero console errors across every step. Verification
  processes cleaned up, `.env.local` reverted, scratch DB removed.

## Explicitly still open

MFA for admin paths — discussed with the user (concrete example given:
what an admin surface worth gating would look like, e.g. a "rotate the
master API key" or "delete all tenant data" button), but the user hasn't
decided whether this project needs an admin panel at all yet. No board
opened; revisit only once that's decided.
