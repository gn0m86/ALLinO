# Sprint 18 — Scheduler Worker

Opened: 2026-07-02. Closed: 2026-07-02.

## Context

User asked (plain-language `AskUserQuestion`, see CURRENT_STATE.md 2026-07-02 entry)
to defer both Google Calendar push and WhatsApp/Viber webhook-receiver architecture.
After seeing the explanation of what a "scheduler" component would unlock, user asked
for an effort estimate, then explicitly said to build it ("делай - это очень полезно
для людей").

## Scope decision

Built the scheduler as the minimal useful thing, not the maximal one:

- **In scope:** a worker process that makes `poll_interval_seconds` on Generic HTTP
  Connectors actually work. That field has existed since Sprint 10
  (`0010_generic_connectors.sql`) but nothing ever read it — sync was always
  externally triggered. This sprint wires it up for real.
- **Explicitly out of scope:** Google Calendar watch-channel renewal and any new
  scheduled-job table. Google Calendar push itself is still deferred (separate
  decision, unchanged). Added no new DB table — due-ness is computed from the
  already-existing `connectors.last_synced_at` column (keyed by
  `{tenant_id}:generic:{slug}`) compared against `poll_interval_seconds`, so this
  stays a pure worker-process addition, not a new persisted concept. If a second
  job type is ever added (e.g. Calendar renewal), *then* a generic `scheduled_jobs`
  table becomes worth it — not before.

## What was built

- `backend/app/services/connector_sync.py` (new): extracted the generic-connector
  fetch+ingest logic out of `backend/app/api/generic_connectors.py`'s
  `sync_generic_connector_config` endpoint into `sync_generic_connector()` /
  `record_batch_result()`, so the manual `/sync` endpoint and the new scheduler
  worker call the exact same code path — no duplicated logic, no drift risk.
  `GenericConnectorSyncError` wraps failures so the API layer can still map them to
  a 502 the same way it always did.
- `backend/app/workers/scheduler_worker.py` (new): mirrors the shape of the existing
  `event_bus_worker.py` (same `--healthcheck` CLI flag, same `main()`/loop
  structure) but polls the DB instead of Redis. `run_scheduler_tick()` lists all
  active generic connectors (any tenant) with `poll_interval_seconds` set, checks
  each against `connectors.last_synced_at` via `_is_due()`, and syncs the due ones.
  Added `--once` (not present on `event_bus_worker`) for testability and one-shot
  ops use.
- New repo functions: `generic_connectors_repo.list_generic_connectors_with_polling()`
  (cross-tenant — the scheduler has no single-tenant request context) and
  `connectors_repo.get_connector(connector_id)` (single-row lookup by id).
- New config: `ALLINO_SCHEDULER_WORKER_POLL_INTERVAL_SECONDS` (default 30) — the
  worker's own tick rate, i.e. how often it checks what's due; unrelated to any
  individual connector's `poll_interval_seconds`.
- `docker-compose.yml`: new `scheduler_worker` service, same pattern as
  `event_bus_worker` (own container, own healthcheck, shared `allino_data` volume).
- Tests: `backend/tests/test_scheduler_worker.py` (new) — due/not-due logic (never
  synced, no interval set, recent sync, stale sync), tick behavior (only due
  connectors sync, failures are recorded without crashing the tick, connectors
  without a `base_url` are skipped), healthcheck.

## Verified

- `pytest -q`: 260 passed (up from 252).
- `ruff check app tests --select F,E9`: clean.
- **Live, real-process verification** (not just unit tests with mocks): started the
  real backend against a scratch SQLite DB, registered a Generic HTTP Connector
  through the real API pointing at a local mock HTTP source, then ran
  `python -m app.workers.scheduler_worker --once` as a separate real process —
  never called `/sync` manually. Confirmed the event landed in the inbox and
  `connectors.last_synced_at` was set. Ran a second tick immediately after: `0
  connector(s) synced` — interval correctly respected. Ran a third tick after
  waiting past the 30s window (the two tool round-trips already exceeded it) —
  correctly synced again. Scratch DB/mock server cleaned up (temp dir outside the
  repo).

## No UI changes

Backend-only; no frontend surface, so no browser verification step applies here —
the live-process run above is the equivalent "don't trust build/tests alone" check
for a backend worker.
