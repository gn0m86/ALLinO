# Sprint 19 — Google Calendar auto-polling via the scheduler worker

Opened: 2026-07-03. Closed: 2026-07-03.

## Context

User asked whether Google Calendar could already be auto-synced now that the
scheduler worker exists (built Sprint 18). Correct instinct, wrong premise:
`scheduler_worker.run_scheduler_tick()` (Sprint 18) was hardcoded to
`list_generic_connectors_with_polling()` — it only reads `poll_interval_seconds`
from the `generic_connector_configs` table. Google Calendar is a built-in
connector with no equivalent persisted per-tenant config row: unlike Generic
HTTP Connectors (registered via API with `tenant_id`/`base_url`/etc ahead of
time), the `connectors` registry row for a built-in source is created lazily,
only on first sync, and `calendar_id` is supplied per-request, not stored.

Asked the user (plain-language `AskUserQuestion`) which of the two real forks
to take:

1. **Real Google Push API** (watch-channel subscriptions, weekly renewal cron,
   public webhook endpoint) — this is genuinely new architecture, previously
   deferred (see Sprint 17/18 fork-decision entries in CURRENT_STATE.md) and
   stays deferred; not what was built here.
2. **Simple periodic polling**, reusing the existing scheduler worker.

User picked (2). Then asked how to solve the "no persisted per-tenant config"
gap specifically:

1. **Env-scoped config** (single tenant/calendar per deployment, matches how
   `ALLINO_GOOGLE_CALENDAR_TOKEN` already works — one token, not per-tenant).
2. Persisted per-tenant config table + new settings API (more general, but
   real new write-surface/auth/tests/frontend for a feature currently needed
   by one tenant).

User picked (1) — env-scoped, recommended option.

## Scope decision

- **In scope:** `ALLINO_GOOGLE_CALENDAR_POLL_ENABLED` / `_INTERVAL_SECONDS` /
  `_TENANT_ID` / `_CALENDAR_ID` env vars. When enabled, the scheduler worker
  also checks (and syncs, if due) exactly one tenant/calendar per tick, using
  the existing `connectors.last_synced_at` due-check pattern from Sprint 18,
  keyed by `{tenant_id}:google_calendar`.
- **Explicitly out of scope:** real Google Push API / watch-channel renewal
  (separate architecture decision, still deferred — unchanged from Sprint
  17/18); polling more than one tenant's calendar per deployment (would need
  the persisted-config-table path, not chosen); auto-polling any other
  built-in connector (Zoom/Teams/Slack/etc.) — this sprint only touches
  Google Calendar, the one the user actually asked about. If a second
  built-in source needs auto-polling later, extend the same env-scoped
  pattern per-source rather than generalizing prematurely.

## What was built

- `backend/app/core/config.py`: new `ALLINO_GOOGLE_CALENDAR_POLL_ENABLED`
  (bool, default false), `ALLINO_GOOGLE_CALENDAR_POLL_INTERVAL_SECONDS`
  (float, default 900), `ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID` (str | None),
  `ALLINO_GOOGLE_CALENDAR_POLL_CALENDAR_ID` (str, default `"primary"`).
- `backend/app/services/connector_sync.py`: new `sync_google_calendar_connector()`
  + `GoogleCalendarSyncError`, mirroring the existing `sync_generic_connector()`
  / `GenericConnectorSyncError` pattern from Sprint 18 exactly — builds a
  `GoogleCalendarConnector`, fetches, then calls the same shared
  `record_batch_result()` used by every other sync path (manual endpoint
  included). No duplicated ingest/telemetry/audit logic.
- `backend/app/workers/scheduler_worker.py`: new `_is_google_calendar_due()`
  (same shape as `_is_due()`, but keyed off the env-configured tenant instead
  of a DB config row) and `run_scheduler_tick()` extended to check it after
  the generic-connector loop and sync via `sync_google_calendar_connector()`
  if due.
- `backend/.env.example` and `docker-compose.yml` (`scheduler_worker` service)
  updated with the new env vars, plus `ALLINO_SCHEDULER_WORKER_POLL_INTERVAL_SECONDS`
  documented in `.env.example` for the first time (existed since Sprint 18 but
  was never added there).
- Tests: `backend/tests/test_scheduler_worker.py` extended with 7 new tests —
  due-check logic (disabled, no tenant configured, never synced, recently
  synced, interval elapsed) and tick behavior (syncs when due, records failure
  without raising).

## Verified

- `pytest -q`: 267 passed (up from 260).
- `ruff check app tests --select F,E9`: clean.
- **Live, real-process verification** (not just unit tests with mocks): ran
  `python -m app.workers.scheduler_worker --once` as a real separate process
  against a scratch SQLite DB (no Google token configured, so zero events
  fetched — this exercises the full wiring, not the Google API call itself).
  First tick: `1 connector(s) synced` (never synced before) and
  `connectors` table got a `tenant_demo:google_calendar` row with
  `status=healthy`. Second tick immediately after: `0 connector(s) synced`
  — the 900s interval correctly not elapsed yet. Scratch DB removed after.

## No UI changes

Backend-only; no frontend surface touched, so no browser verification step
applies here — the live-process run above is the equivalent check.
