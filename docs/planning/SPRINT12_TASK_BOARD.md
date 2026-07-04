# Sprint 12 Task Board

Opened: 2026-07-01

## Scope decision

`PROJECT_MASTER_BRIEF.md` §C lists Wave 1 Optional as: Slack (done, Sprint 4) and
"Google Calendar/Meet (с авто-renew watch channels)". `CLAUDE.md` §3 also lists
Google Calendar/Meet under Wave 1 Optional. It was the one connector from Wave 1
(core or optional) never implemented — confirmed by grep before starting, zero
hits for "google"/"calendar" in `backend/app` prior to this sprint.

This sprint scopes **only** the REST-polling connector baseline, matching the
on-demand-sync pattern every other connector in this codebase already uses
(none of the 9 existing connectors have an internal poll scheduler either —
Sprint 10's task board explicitly noted this as an existing pattern, not a
gap). The "авто-renew watch channels" (push API, 7-day channel expiry
requiring a renewal cron) is explicitly **out of scope** for this board — it
needs new scheduler infrastructure this project doesn't have yet, and
`PROJECT_MASTER_BRIEF.md` §C already earmarks "hardening ... Google Calendar"
as a separate Wave 2 line item, i.e. push/watch-channel support was always
meant to land after the baseline connector, not with it.

## S12-01: Google Calendar/Meet connector (REST polling, on-demand sync)

Status: closed

- `backend/app/connectors/google_calendar_connector.py`: `GoogleCalendarConnector`
  on the same `BaseConnector` contract as the other 9 connectors (start/stop/health/
  fetch_events, `RetryPolicy`/`run_with_retry` reuse — inherits the existing
  429/5xx-retry, 4xx-fail-fast HTTP-aware policy for free).
- Auth: `ALLINO_GOOGLE_CALENDAR_TOKEN` (pre-issued OAuth2 access token via env/Vault),
  same simplification already used for Zoom/Teams in this codebase — this service
  treats it as an opaque bearer token and does not implement the OAuth refresh
  dance in-app.
- Maps Google Calendar Events API `items[]` (`GET /calendars/{id}/events`) to
  UnifiedEvent: event id, summary, organizer email, `start.dateTime`/`start.date`,
  `htmlLink`, and a Meet URL resolved from `conferenceData.entryPoints` (preferring
  the `video` entry point) with a fallback to the legacy `hangoutLink` field.
  Cancelled events (`status: "cancelled"`) get a `[Cancelled]` preview prefix so
  they're visually distinct in the inbox without needing a priority-classifier
  special case (the existing keyword-based classifier already has no
  Calendar-specific logic, same as it has none for Zoom/Teams).
- New sync endpoint: `POST /api/v1/ingestion/connectors/google_calendar/sync`
  (tenant-scoped, `require_connector_sync_permission`, optional `calendar_id`
  override — defaults to `primary`), reusing the shared `_run_connector_sync(...)`
  helper — telemetry, connector-registry upsert, run history, event-bus routing,
  and audit logging all come for free, no new code paths.
- Capability matrix (`GET /connectors/capabilities`) and frontend `Sidebar.tsx`
  source map updated with a `google_calendar` entry, following the exact pattern
  of every prior connector addition.
- Tests: `backend/tests/test_google_calendar_connector.py` (mapping incl.
  conferenceData vs. hangoutLink precedence, cancelled-status preview prefix,
  seeded fetch, retry success/exhaustion, 401 fail-fast, 429 retry),
  `backend/tests/test_google_calendar_sync_endpoint.py` (seeded ingest, error-path
  persistence, 401 fail-fast at the endpoint level) — same shape as the existing
  Zoom/Teams endpoint tests. `test_connector_capabilities_endpoint.py` extended
  for the new source.
- Verified: backend `pytest -q` => 202 passed (up from 191);
  `ruff check app tests --select F,E9` => all checks passed. Frontend:
  `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification (per CLAUDE.md §6, mandatory — not skipped even
  though this connector follows an established pattern): seeded one confirmed
  and one cancelled Google Calendar event via the sync endpoint against a real
  running backend, confirmed in a real browser that: the Sources panel shows
  `google_calendar` as healthy with sync telemetry, the Connector Operations
  panel and Recent Runs both show the sync, the inbox filter bar gets a
  `google_calendar` chip, both events render in the inbox list (cancelled one
  flagged high-priority), and opening the cancelled event's thread renders
  correctly with the composer honestly stating "Replies aren't supported for
  google_calendar yet" (no fake always-on composer — this connector was
  deliberately not added to `REPLY_SUPPORTED_SOURCES`, replies are chat-shaped
  for Telegram/Slack only, a calendar event has no reply semantics). Zero
  unexpected console errors.

## Explicitly out of scope for this sprint

- Push/watch-channel support (`events.watch`) and the associated 7-day
  renewal cron — needs new scheduler infrastructure; tracked as a future
  hardening item per `PROJECT_MASTER_BRIEF.md` §C, not silently dropped.
- OAuth2 authorization-code / refresh-token flow inside the app — this
  connector consumes a pre-issued access token exactly like Zoom/Teams already
  do in this codebase.
- Reply/write-back for `google_calendar` — a calendar event isn't a chat
  message; no reply semantics apply, so it was correctly left out of
  `REPLY_SUPPORTED_SOURCES` rather than stubbed.
