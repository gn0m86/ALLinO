# Sprint 30 — Four "make it actually usable" improvements: auto-sync, sync-now, TOTP QR, activity digest

Opened: 2026-08-14. Closed: 2026-08-14.

## Context

User asked for a project readiness assessment ("что дальше можно улучшать...
проект готов или нет?"). Answer: functionally complete for the local-first
MVP scope, but with one real practical blocker — none of the 10 built-in
named connectors (GitHub, GitLab, Jira, Linear, Telegram, Slack, Discord,
Zoom, Teams, Rocket.Chat) had any automatic recurring sync; only Generic
HTTP Connectors and one env-configured Google Calendar tenant did. Everything
else required an external trigger (manual API call / cron) to ever pull new
data. User asked to fix that plus three more items in one pass: a "Sync now"
button, QR-code TOTP enrollment, and an activity digest. WhatsApp/Viber
(mentioned earlier in the conversation) was explicitly deferred by the user
mid-session ("пока отложи"). A fifth item, a *local AI* priority classifier
(Ollama), was explicitly separated out and NOT built this sprint — it means
running a separate LLM inference service, not just more application code, a
different category of change from the other four.

Executed sequentially, not via parallel subagents, since all four items
share overlapping files (`scheduler_worker.py`, `SettingsPanel.tsx`) that
would conflict if edited concurrently by isolated agents.

## 1) Auto-sync for built-in connectors

- `backend/app/core/config.py`: `ALLINO_BUILTIN_CONNECTORS_POLL_ENABLED` /
  `_INTERVAL_SECONDS` / `_TENANT_ID` — same env-scoped-to-a-single-tenant
  shape as the existing Google Calendar poll config (Sprint 19); no
  persisted per-tenant config table exists for built-ins, so this isn't
  multi-tenant.
- `backend/app/services/connector_sync.py`: new `sync_builtin_connector()` +
  `BuiltinConnectorSyncError`, mirroring `sync_google_calendar_connector()`
  exactly (reuses the existing `record_batch_result()` helper — no new
  telemetry-recording logic needed).
- `backend/app/workers/scheduler_worker.py`: `_BUILTIN_CONNECTOR_SPECS`
  (source, connector class, required-secret env var name) for all 10
  sources; `_is_builtin_connector_due()` (same due-check shape as the
  existing generic/calendar checks, keyed `f"{tenant_id}:{source}"`); a new
  block in `run_scheduler_tick()` that skips any source whose secret isn't
  configured (`has_secret_value`), then syncs the rest that are due.
- **Found and fixed a real pre-existing deployability gap while wiring this
  up**: `docker-compose.yml` never forwarded ANY of the 10 built-in
  connector token env vars (`ALLINO_GITHUB_TOKEN`, etc.) to the `backend`
  or `scheduler_worker` services — only Wave 2's Discord/Zoom/Teams/Google
  Calendar tokens were even documented in `.env.example`, and none of Wave
  1's (GitHub/GitLab/Jira/Linear/Telegram/Slack) were. This meant a
  `docker compose up` deployment could never configure these connectors at
  all, regardless of auto-sync. Fixed: all 10 tokens (+ GitLab/Jira
  base_url, Slack/Discord channel_id, Rocket.Chat's 4-part config) now
  documented in `.env.example` and forwarded in `docker-compose.yml` for
  both services; also added `ALLINO_ADMIN_TOTP_SECRET` to `docker-compose.yml`
  (same gap, needed for admin actions to work in a compose deployment).
- Tests: 7 new tests in `test_scheduler_worker.py` (disabled-skips,
  no-secret-skips, due/not-due transitions, success + failure paths mirror
  the existing Google Calendar test shapes exactly).
- **Live-verified as a real subprocess** (no UI involved, so no browser
  step needed — same precedent as Sprint 18's scheduler verification):
  ran `python -m app.workers.scheduler_worker --once` three times against a
  scratch DB: (1) enabled with zero tokens configured → 0 syncs attempted,
  no crash; (2) with a real (but invalid) `ALLINO_GITHUB_TOKEN` → a real
  HTTP call to `api.github.com`, a real `401`, captured gracefully in the
  connector registry (`status=error`, `last_error` populated) without
  crashing the worker process.

## 2) "Sync now" button

- `frontend/src/lib/api.ts`: `syncConnector(sourceType)` — `POST
  /api/v1/ingestion/connectors/{source}/sync` with an empty body (every
  sync request model's fields are optional, confirmed by reading
  `ingestion.py`).
- `frontend/src/components/SettingsPanel.tsx`: extracted the "Connected
  Sources" row into a new `ConnectedSourceRow` sub-component (own
  pending/message state per row), added a "Sync now" button shown only
  when `available && configured && sync_supported` — i.e. never shown for
  an unconfigured source, matching the existing `rowLabel`/`rowColor`
  logic.
- **Live-verified**: with `ALLINO_GITHUB_TOKEN` set to an invalid value,
  clicked "Sync now" — a real `502` came back (invalid credentials
  upstream), the row showed "github connector sync failed" inline, button
  re-enabled. No CORS issue (method/headers already whitelisted from prior
  sprints).

## 3) QR-code TOTP enrollment

- **Deliberately NOT a server endpoint or web UI feature.** An endpoint
  that could hand back the raw TOTP seed would let any caller holding
  today's first factor (API key) permanently self-enroll a device and
  bypass the second factor going forward — defeats the entire point of
  Sprint 26's admin-MFA design (TOTP is checked unconditionally, even for
  trusted API-key callers, specifically so holding the API key alone is
  never sufficient).
- Instead: new local-only CLI script,
  `backend/scripts/generate_admin_totp_qr.py`. Generates (or accepts
  `--secret`) a base32 secret, builds the `otpauth://` URI via
  `pyotp.provisioning_uri()`, and renders it as an ASCII QR code in the
  terminal (or saves a PNG with `--output`). Never talks to the running
  backend or any network. `qrcode[pil]` added to `requirements-dev.txt`
  (dev/utility-only, never imported by the running server).
- Fixed a real Windows-specific bug found while testing: `qrcode`'s ASCII
  output uses Unicode block characters that Windows' default console
  codepage (cp1251 here) can't encode, crashing with `UnicodeEncodeError`.
  Fixed via `sys.stdout.reconfigure(encoding="utf-8")` before printing —
  works identically on Windows/macOS/Linux now.
- `.env.example`'s admin-MFA section updated to point at the script instead
  of the old "type the secret by hand" instruction (manual entry still
  works too, mentioned as an alternative).
- Tests: `test_generate_admin_totp_qr_script.py` (2 tests) — verifies the
  built URI is well-formed and round-trips through `pyotp.parse_uri()` /
  `.verify()`. QR rendering itself isn't unit-tested (a display concern);
  verified manually instead (ASCII output to a real Windows terminal, and
  PNG file output, both confirmed working).

## 4) Activity digest (rule-based, not AI)

- `backend/app/db/repositories/messages_repo.py`: `digest_messages()` —
  active messages with `created_at >= now - since_hours` (ingestion time,
  not the source event's own `timestamp`, so a re-synced old event doesn't
  count as "new since last check").
- `backend/app/services/digest.py`: `build_digest()` — pure aggregation
  (counts by source, counts by priority, top 10 high-priority
  "highlights"). Zero AI/external calls, zero new dependencies — just a
  loop over data already in the local database.
- `backend/app/api/ingestion.py`: `GET /digest?hours=24` (default),
  `require_ingestion_read_permission` (same tier as `/inbox`, `/search`).
- Frontend: `fetchDigest()` in `lib/api.ts`, new `DigestResponse` type,
  new `components/DigestPanel.tsx` (self-fetching, reuses `InboxList` for
  highlights — same pattern as `SearchPanel`). Wired into `page.tsx` as a
  third content-swap state alongside Archived/Search (a `ClockIcon` button
  in the Inbox header, "Digest" panel with a "Back to Inbox" header,
  mutually exclusive with Archived/Search by the same structural
  convention those two already use — the toggle buttons only exist in the
  base view). Not a 6th L1 nav section.
- Tests: 6 new tests in `test_digest.py` (counts by source/priority,
  highlights-only-high-priority, time-window exclusion via a
  backdated `created_at`, archived-exclusion, tenant isolation, default
  24h window).
- **Live-verified**: seeded 3 messages (2 github incl. one "critical
  outage" text, 1 slack); Digest panel showed "3 new messages in the last
  24h", `github: 2` / `slack: 1`, `Normal: 2` / `High: 1`, one highlight
  (the critical-outage message); clicking the highlight closed the digest
  and opened that message's thread correctly. Zero console errors.

## Explicitly out of scope (stated, not silent)

- **Local AI priority classifier (Ollama)** — separated out from this
  sprint on purpose. Running a local LLM inference engine is new
  infrastructure (a service to run, a model to download, real CPU/RAM
  footprint), not an incremental code change like the other four items.
  Revisit as its own sprint if wanted.
- WhatsApp Business / Viber — user explicitly said to hold off mid-session.
  Still needs its own architecture decision (webhook-receiver connector
  shape) whenever it's picked back up.
- Multi-tenant auto-sync for built-ins — same single-env-tenant limitation
  as Google Calendar polling; a real multi-tenant version would need a
  persisted per-tenant connector-config table these built-ins don't have.

## Verified

- Backend: `pytest -q` => 324 passed (up from 309: 7 scheduler + 6 digest +
  2 TOTP-script tests). `ruff check app tests --select F,E9` => all checks
  passed (the exact CI-gated scope; a pre-existing unrelated `F401` in
  `scripts/validate_staging_smoke_wave2.py`, outside this scope, was left
  alone as out-of-scope for this sprint).
- Frontend: `tsc --noEmit` clean; `npm run build` success.
- `docker-compose.yml` re-validated as parseable YAML after the token
  wiring changes.
- **Live verification**: scheduler auto-sync as a real subprocess (see
  above); Sync-now button and Digest panel both live-verified in a real
  browser against a real backend (zero unexpected console errors in
  either session); TOTP QR script run for real (ASCII to terminal + PNG
  file), including catching and fixing a genuine Windows encoding bug.
  Verification processes cleaned up, `.env.local` reverted, scratch DBs
  removed.
