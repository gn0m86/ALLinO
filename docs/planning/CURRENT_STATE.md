# ALLinO Current State

Updated: 2026-06-25
Purpose: one-file handoff for future sessions and AI agents.

## 1) What is implemented now

Backend vertical slice is working end-to-end:

- Ingestion API:
  - POST /api/v1/ingestion/events
  - POST /api/v1/ingestion/seed
  - POST /api/v1/ingestion/validate (dry-run)
  - GET /api/v1/ingestion/inbox
  - GET /api/v1/ingestion/audit
  - GET /api/v1/ingestion/stats
- Health endpoint:
  - GET /health
- Persistence:
  - SQLite with startup migration apply
  - migrations: 0001_init.sql, 0002_rls.sql (SQLite no-op + Postgres template)
- Core services:
  - normalization
  - dedup (idempotency key hash)
  - append-only audit write path
- Connector framework:
  - base adapter contract with lifecycle hooks (start, stop, health)
  - retry policy contract
  - mock connector implementation for integration without provider APIs
- Tenant isolation (current scope):
  - tenant-scoped reads on inbox/audit/stats via required tenant context
  - app-level tenant filtering in repositories
  - SQLite mode uses RLS template migration for Postgres hardening path

Frontend runtime setup is now implemented:

- Next.js packaging (`package.json`, `tsconfig.json`, `next.config.mjs`)
- local env template (`.env.example` -> `.env.local`)
- app build and dev runtime verified

CI baseline is now in place for backend:

- workflow: .github/workflows/backend-ci.yml
- checks: ruff (pyflakes-level), pytest, compileall build check
- dev dependencies: backend/requirements-dev.txt

## 2) Last verified execution evidence

Smoke runbook was executed successfully after migration path fix.

Observed outputs:

- health_status: ok
- seed_inserted: 5
- seed_duplicates: 0
- inbox_count_observed: 5
- audit_count_observed: 6
- ingest_status: inserted
- validate_status: valid
- stats_inbox_count: 6
- stats_audit_count: 7

Additional test evidence:

- `pytest tests/test_connector_contract.py -q` -> `1 passed`
- `ruff check app tests --select F` -> `All checks passed`
- `pytest tests -q` -> `1 passed`
- `python -m compileall app` -> success
- `pytest tests/test_tenant_isolation.py -q` -> `1 passed`

Additional runtime evidence:

- tenant smoke (A/B):
  - tenant_a inbox_count = 2, tenant_b inbox_count = 1
  - inbox responses contained only their own tenant ids
  - tenant-scoped stats returned isolated counts
- frontend runtime:
  - `npm --prefix frontend run dev` -> Next.js ready at `http://localhost:3000`
  - `npm --prefix frontend run build` -> successful production build

## 3) Important fix history

- Fixed migration path in backend/app/db/session.py:
  - from BASE_DIR.parent / "migrations"
  - to BASE_DIR / "migrations"
- Reason: previous path prevented table creation and caused runtime 500 errors (no such table).

## 4) Current stage

Updated: 2026-07-01

Project stage: Sprint 2 CLOSED. Sprint 3 planning initialized.

Done in practice:

- repo scaffold and baseline docs
- unified schema and examples
- ingestion + normalization + persistence + inbox read path
- audit endpoint and append flow
- connector adapter contract + mock connector + basic connector test
- smoke runbook and quickstart docs
- Sprint 2 kickoff: connector shortlist (GitHub, GitLab, Linear)
- S2-02 complete: GitHub connector end-to-end ingest + persist + smoke path
- S2-03 complete: GitLab connector end-to-end ingest + persist + smoke path
- S2-04 complete: Linear connector end-to-end ingest + persist + smoke path

2026-06-30 — Design system integrated:

- Design handoff: `docs/design_handoff_secure_inbox/` (HTML spec + tokens.css + README)
- Chosen direction: Quiet Slate / light (WCAG AA)
- `frontend/src/app/globals.css` — full token set live in app
- `frontend/src/app/layout.tsx` — `data-direction="slate" data-theme="light"`, Google Fonts
- `frontend/src/components/Icons.tsx` — 12 inline SVG icons
- All components redesigned: Sidebar (218px rail), InboxList (spec InboxItem), ThreadPanel (header + SecurityCard + composer), page.tsx (3-pane layout)
- CLAUDE.md § 6 updated with design rules for all future UI work

2026-06-30 — Security hardening:

- `.gitignore` at root — `.env.local`, `allino.db`, `.venv/`, `.next/` protected
- `core/config.py` + `core/security.py` — `ALLINO_API_KEY` env var; all ingestion endpoints require `X-API-Key` if set
- `Depends(resolve_tenant_id)` added to `/events`, `/validate`, `/seed` (previously unprotected)
- Tenant mismatch guard — `event.tenantId != tenant_id` → 403 on direct endpoints; silent reject in connector batch
- `_process_connector_batch()` — removed 3× duplication of connector sync loop
- `limit` clamped `ge=1, le=1000` via `Query()` on `/inbox`, `/audit`, `/seed`
- `extra="forbid"` on `UnifiedEvent` — unknown fields → 422
- CORS tightened to `GET, POST` + explicit headers list
- `lifespan` replaces deprecated `@on_event("startup")`
- Migration tracking: `schema_migrations` table, `init_db()` skips already-applied migrations
- `0003_hardening.sql` — `idx_audit_logs_tenant_time` index
- `frontend/src/lib/api.ts` — reads `NEXT_PUBLIC_BACKEND_URL` from env, sends `X-Tenant-Id` header
- `backend/.env.example` created

2026-06-30 — Sprint 2 completion (S2-05..S2-10):

- S2-05: dedup strategy — `services/dedup.py`, `test_ingestion_idempotency.py` (7 tests: unit + API-level)
- S2-06: priority classifier — `services/priority_classifier.py`, integrated in `normalizer.py`, `InboxMessage.priority` field, `test_priority_classifier.py`
- S2-07: thread context linking — `page.tsx` groups same-source events as `relatedItems`, `ThreadPanel` renders related events panel (max 5 + overflow counter)
- S2-08: inbox filters — `FilterBar.tsx` (source/priority chips, toggle/clear), mode-based auto-filter (focus/incident → priority=high)
- S2-09: error/empty states — loading skeleton, error banner (danger-soft), empty state for filtered list, empty state for no items
- S2-10: observability — `services/metrics.py` MetricsStore (thread-safe), connector health/retry/lag tracking, `GET /api/v1/ingestion/metrics`
- All 33 tests pass

2026-07-01 — Sprint 2 formally closed, task board synchronized.

2026-07-01 — W1-08 and CI cleanup:

- `docker-compose.yml` — updated with ALLINO*API_KEY env var, NEXT_PUBLIC*\* as build args (not runtime env), backend healthcheck, `depends_on: condition: service_healthy`
- `frontend/Dockerfile` — ARG/ENV for NEXT_PUBLIC_BACKEND_URL and NEXT_PUBLIC_TENANT_ID before `npm run build`
- `frontend/.dockerignore` + `backend/.dockerignore` — exclude node_modules, .next, .venv, data/, tests/
- `frontend/package.json` — added `typecheck: tsc --noEmit` script
- `.github/workflows/frontend-ci.yml` — typecheck + production build CI

2026-07-01 — Security + registry hardening (post-review follow-up):

- Auth policy hardened in `core/security.py`: fail-closed when `ALLINO_API_KEY` is missing outside explicitly allowed local dev mode.
- New env controls in `core/config.py`: `ALLINO_ENV`, `ALLINO_ALLOW_INSECURE_DEV`; `.env.example` updated.
- DB-level append-only for `audit_logs`: migration `0005_audit_append_only.sql` with UPDATE/DELETE blocking triggers.
- Connector registry wired: `db/repositories/connectors_repo.py` + sync endpoints now upsert connector status into `connectors` table.
- Log sanitization added for ingestion rejected-event metadata (`_redact_secrets`) and connector token accepted only via `X-Connector-Token` header (body token fallback removed).
- Test suite extended:
  - `test_api_key_security.py`
  - `test_audit_append_only.py`
  - `test_ingestion_security_sanitization.py`
  - `test_metrics.py` tenant-scoped API assertion
  - `test_connectors_endpoint.py` tenant-scoped connector registry API
  - connector sync endpoint tests assert connector registry rows
- Current backend test status: 49/49 passed.

2026-07-01 — Backend-driven thread linking contract:

- Domain model update: `InboxMessage.thread_key` added in `domain/events.py`.
- Normalization update: `services/normalizer.py` now computes deterministic `thread_key` from stable payload anchors (`subject_url` / `target_url` / `url` / `identifier` / repo/project/team) with fallback.
- DB update: migration `0007_thread_key.sql` adds `messages.thread_key`.
- Repository update: `messages_repo.py` now persists and returns `thread_key`.
- Frontend contract update:
  - `frontend/src/lib/types.ts` includes `InboxMessage.thread_key`
  - `frontend/src/app/page.tsx` uses backend-provided `thread_key` for related thread items (replaces client-only heuristic)
- Tests:
  - new `test_thread_key.py` validates stability and differentiation paths.

2026-07-01 — JWT auth hardening (security gate progress):

- `core/config.py` adds JWT config:
  - `ALLINO_JWT_SECRET`
  - `ALLINO_JWT_ALGORITHM`
  - `ALLINO_JWT_ISSUER`
  - `ALLINO_JWT_AUDIENCE`
- `core/security.py` upgraded auth dependency:
  - accepts valid `X-API-Key` and/or JWT Bearer token
  - fail-closed outside explicit insecure local dev mode
  - returns 503 when no auth secret is configured in non-dev
- `requirements.txt` updated with `PyJWT==2.9.0`.
- `tests/test_api_key_security.py` extended with JWT scenarios:
  - valid JWT accepted
  - invalid JWT rejected
  - API key + JWT mixed mode accepted
- `.env.example` documents optional JWT settings.

2026-07-01 — JWT authorization policy for connector sync:

- `core/config.py` adds permission config:
  - `ALLINO_JWT_SYNC_ROLES` (default: `admin,operator`)
  - `ALLINO_JWT_SYNC_SCOPES` (default: `connectors:sync,sync:connectors`)
- `core/security.py` adds `require_connector_sync_permission(...)`:
  - API-key callers are allowed as operational path
  - JWT Bearer callers must include allowed role or scope for connector sync
  - insufficient claims => `403`
- `api/ingestion.py` connector sync endpoints now require this permission dependency.
- `test_api_key_security.py` extended with authorization tests:
  - role-based allow
  - scope-based allow
  - missing claims => forbidden
  - API-key bypass path remains valid

2026-07-01 — Connector telemetry hardening (backend + frontend):

- New DB migration: `0006_connectors_telemetry.sql` adds operational fields on `connectors`:
  - `last_synced_at`, `last_error`
  - `last_processed`, `last_inserted`, `last_duplicates`, `last_rejected`
  - `updated_at`
- `db/repositories/connectors_repo.py` updated to upsert/list full telemetry snapshot.
- `api/ingestion.py` connector sync endpoints refactored through shared `_run_connector_sync(...)`:
  - writes success telemetry on normal sync
  - writes `status=error` + `last_error` on sync failure
  - returns 502 for connector sync failures
- `test_connectors_endpoint.py` extended:
  - asserts telemetry fields in API response
  - verifies error-path updates connector registry state
- Frontend sources panel upgraded to show per-source telemetry:
  - `sync` time, processed/inserted/rejected counters, error marker
  - polling remains resilient with manual refresh + backoff.

2026-07-01 — Frontend connector operations UX (live monitoring):

- `frontend/src/app/page.tsx` now uses resilient connector refresh loop:
  - base poll interval 15s
  - exponential backoff on failures up to 120s
  - abort-safe fetches on unmount/restart
- `frontend/src/components/Sidebar.tsx` now includes:
  - manual refresh button for connector states
  - refreshing indicator
  - last successful update timestamp
  - retry counter visibility when refresh fails
- `frontend/src/lib/api.ts` supports `AbortSignal` for inbox/connectors fetch calls.

2026-07-01 — Connector runs history + API authorization integration coverage:

- Backend: historical sync runs persisted in new `connector_runs` table via migration `0008_connector_runs.sql`.
- Backend repository: `db/repositories/connector_runs_repo.py` adds append + tenant-scoped listing with source filter and limit.
- Backend API:
  - `api/ingestion.py` now appends run records on both success and error paths in `_run_connector_sync(...)`.
  - new endpoint `GET /api/v1/ingestion/connectors/runs` (tenant-scoped, `limit`, optional `source`).
- Backend tests:
  - new `test_connector_runs_endpoint.py` validates success history, source filter, and error-run capture.
  - new `test_sync_permissions_api.py` validates endpoint-level JWT authorization behavior (`403` missing claims, `200` with `connectors:sync` scope).
  - current backend test status: 58/58 passed.
- Frontend integration:
  - `frontend/src/lib/types.ts` adds `ConnectorRun` contract.
  - `frontend/src/lib/api.ts` adds `fetchConnectorRuns(...)`.
  - `frontend/src/app/page.tsx` fetches connector statuses + runs in one polling cycle.
  - `frontend/src/components/Sidebar.tsx` renders a "Recent Runs" list with source/status/time and p/i/d/r counters + error hint.
  - `npm --prefix frontend run build` passes after integration.

2026-07-01 — Fine-grained JWT policy (phase 2) for ingestion read endpoints:

- Config update in `core/config.py`:
  - `ALLINO_JWT_READ_ROLES` (default: `admin,operator,analyst,viewer`)
  - `ALLINO_JWT_READ_SCOPES` (default: `ingestion:read,inbox:read,audit:read,metrics:read,connectors:read`)
- Security update in `core/security.py`:
  - new dependency `require_ingestion_read_permission(...)`
  - API-key callers remain trusted operational path
  - JWT callers must provide allowed role or scope for ingestion read-path
  - insufficient claims => `403`
- API wiring in `api/ingestion.py`:
  - read permission dependency added to GET endpoints:
    - `/inbox`, `/audit`, `/stats`, `/metrics`, `/connectors`, `/connectors/runs`
- Tests:
  - `test_api_key_security.py` extended with unit tests for read permission allow/deny paths.
  - new `test_ingestion_read_permissions_api.py` validates endpoint-level behavior (`403` missing claims, `200` with read scope).
  - current backend test status: 64/64 passed.
- `backend/.env.example` updated with new JWT read permission env keys.

2026-07-01 — Thread linking quality tuning for non-URL sources:

- `services/normalizer.py` thread-key strategy improved:
  - strong anchors still prioritized: `subject_url`, `target_url`, `url`, `identifier`
  - added semantic payload anchor for non-URL paths: `repository/project/team + type/state/action/reason`
  - `text` now used only as fallback when structured semantic fields are missing
  - keeps stable grouping for same logical thread while reducing accidental split by transient text changes
- Tests in `test_thread_key.py` extended:
  - non-URL semantic grouping case
  - non-URL semantic separation case
- current backend test status: 66/66 passed.

2026-07-01 — Dedicated telemetry/history panel in frontend:

- New component: `frontend/src/components/ConnectorOpsPanel.tsx`
  - separate operational dashboard (outside Sidebar)
  - current connector statuses with health + last sync time
  - recent connector runs with counters and error hint
- `frontend/src/components/ThreadPanel.tsx` updated:
  - accepts connector telemetry props
  - when no thread is selected, renders `ConnectorOpsPanel` + empty-thread guidance
- `frontend/src/app/page.tsx` now passes connector statuses/runs/refresh metadata into `ThreadPanel`.
- Frontend verification: `npm --prefix frontend run build` passes after integration.

2026-07-01 — Sprint 3 execution started (S3-01 closed):

- Jira integration delivered end-to-end:
  - new connector: `backend/app/connectors/jira_connector.py`
  - mapping: `map_jira_issue_to_unified_event(...)`
  - new sync endpoint: `POST /api/v1/ingestion/connectors/jira/sync`
  - connector registry/runs integration reuses shared `_run_connector_sync(...)`
- Tests added:
  - `backend/tests/test_jira_connector.py`
  - `backend/tests/test_jira_sync_endpoint.py`
- Frontend source list updated with Jira in `frontend/src/components/Sidebar.tsx`.
- Verification:
  - backend: `pytest -q` => 69 passed
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Sprint 3 progress (S3-02 closed):

- Telegram integration delivered end-to-end:
  - new connector: `backend/app/connectors/telegram_connector.py`
  - mapping: `map_telegram_update_to_unified_event(...)`
  - new sync endpoint: `POST /api/v1/ingestion/connectors/telegram/sync`
  - connector registry/runs integration via shared `_run_connector_sync(...)`
- Tests added:
  - `backend/tests/test_telegram_connector.py`
  - `backend/tests/test_telegram_sync_endpoint.py`
- Frontend source maps updated for Telegram/Jira visibility:
  - `frontend/src/components/Sidebar.tsx`
  - `frontend/src/components/ThreadPanel.tsx`
- Verification:
  - backend: `pytest -q` => 72 passed
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Sprint 3 progress (S3-03 closed):

- New backend endpoint: `GET /api/v1/ingestion/connectors/capabilities`
  - tenant-scoped + protected by ingestion read permission dependency
  - returns capability matrix (`source_type`, `available`, `configured`, `requires_secret`, `sync_supported`)
- Backend test added: `backend/tests/test_connector_capabilities_endpoint.py`
- Frontend switched from hardcoded source list to capability-driven rendering:
  - `frontend/src/lib/types.ts` adds `ConnectorCapability`
  - `frontend/src/lib/api.ts` adds `fetchConnectorCapabilities(...)`
  - `frontend/src/app/page.tsx` includes capabilities in connector polling cycle
  - `frontend/src/components/Sidebar.tsx` renders sources from capability payload
- Verification:
  - backend: `pytest -q` => 73 passed
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Sprint 3 progress (S3-04 closed):

- Feature-flagged event-bus start path added for connector sync processing:
  - new service: `backend/app/services/event_bus.py`
  - modes: `direct`, `redis_stream`, `redis_fallback`
  - Redis Streams baseline path with resilient fallback when Redis is unavailable
- Sync pipeline integration:
  - `backend/app/api/ingestion.py` now routes connector event batches through event bus processor
  - sync response now includes `event_bus` mode for observability
- Config + docs:
  - `backend/app/core/config.py` adds `ALLINO_EVENT_BUS_ENABLED`, `ALLINO_REDIS_URL`, `ALLINO_REDIS_STREAM_PREFIX`
  - `backend/.env.example` documents new env flags
  - `backend/requirements.txt` includes `redis`
- Tests added:
  - `backend/tests/test_event_bus.py`
  - `backend/tests/test_event_bus_sync_response.py`
- Verification:
  - backend: `pytest -q` => 76 passed

2026-07-01 — Sprint 3 progress (S3-05 closed):

- Inbox incremental pagination implemented with opaque cursor tokens:
  - repository: `backend/app/db/repositories/messages_repo.py`
    - cursor encode/decode helpers
    - cursor-aware `list_messages(...)`
    - `list_messages_page(...)` returning `items + next_cursor`
  - API: `backend/app/api/ingestion.py`
    - `/api/v1/ingestion/inbox` now supports optional `cursor`
    - new `/api/v1/ingestion/inbox/page` response envelope for incremental polling
- Validation:
  - new `backend/tests/test_inbox_cursor_api.py`
  - invalid cursor returns `400`
  - multi-page retrieval returns disjoint items and non-empty `next_cursor`
- Verification:
  - backend: `pytest -q` => 78 passed

2026-07-01 — Sprint 3 progress (S3-06 closed):

- Frontend operations UX expanded in `frontend/src/components/ConnectorOpsPanel.tsx`:
  - source/status filters for run stream
  - clickable run selection with details block (`id`, source/status, sync time, counters, error text)
  - keeps token-based styling and existing panel placement in thread area
- Verification:
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Sprint 3 progress (S3-07 closed):

- CI hardening applied:
  - `.github/workflows/backend-ci.yml`
    - Python matrix: 3.12 + 3.13
    - lint scope: `ruff --select F,E9`
    - junit artifact upload per matrix job
  - `.github/workflows/frontend-ci.yml`
    - Node matrix: 20 + 22
    - typecheck/build logs captured and uploaded as artifacts

2026-07-01 — Sprint 3 progress (S3-08 closed):

- Added release hardening checklist execution snapshot:
  - `docs/planning/RELEASE_HARDENING_CHECKLIST_S3.md`
  - includes security/data/runtime/CI checks and current GO assessment for ongoing sprint baseline

2026-07-01 — Sprint 4 execution started (S4-01 closed):

- New planning board: `docs/planning/SPRINT4_TASK_BOARD.md`
- Slack integration delivered end-to-end:
  - connector: `backend/app/connectors/slack_connector.py`
  - endpoint: `POST /api/v1/ingestion/connectors/slack/sync`
  - tests: `backend/tests/test_slack_connector.py`, `backend/tests/test_slack_sync_endpoint.py`
  - capabilities matrix updated with `slack` entry
  - Sidebar source visual map updated for Slack
- Verification:
  - backend: `pytest -q` => 81 passed
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Sprint 4 progress (S4-02 and S4-03 closed):

- `docs/planning/SMOKE_RUNBOOK.md` updated with Redis event-bus smoke scenario:
  - env setup for event-bus mode
  - expected `event_bus` response/audit markers
  - fallback expectation when Redis is unavailable
- Frontend inbox path moved to cursor API:
  - `frontend/src/lib/types.ts` adds `InboxPageResponse`
  - `frontend/src/lib/api.ts` adds `fetchInboxPage(...)`
  - `frontend/src/app/page.tsx` uses `/api/v1/ingestion/inbox/page` polling with dedup merge
- Verification:
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Sprint 4 progress (S4-04 and S4-05 closed):

- Capabilities endpoint runtime-awareness improved:
  - `backend/app/api/ingestion.py` now derives `configured` flags from env runtime state
  - `requires_secret` semantics aligned across token-based connectors
  - `backend/tests/test_connector_capabilities_endpoint.py` extended with env-driven assertions
- Release hardening snapshot added for Sprint 4:
  - `docs/planning/RELEASE_HARDENING_CHECKLIST_S4.md`
- Verification:
  - backend: `pytest -q` => 82 passed

Project stage update:

- Sprint 4 board items completed (S4-01..S4-05). Ready for next planning cycle.

2026-07-01 — Sprint 5 execution started (S5-01 closed):

- New planning board: `docs/planning/SPRINT5_TASK_BOARD.md`
- Discord integration delivered end-to-end:
  - connector: `backend/app/connectors/discord_connector.py`
  - endpoint: `POST /api/v1/ingestion/connectors/discord/sync`
  - tests: `backend/tests/test_discord_connector.py`, `backend/tests/test_discord_sync_endpoint.py`
  - capabilities matrix updated with `discord` runtime-configured entry
  - Sidebar source visual map updated for Discord
- Verification:
  - backend: `pytest -q` => 85 passed
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Sprint 5 completed (S5-02..S5-05 closed):

- Capability matrix extended for Wave 2 readiness in `api/ingestion.py`:
  - added `zoom` and `teams` entries with runtime `configured` flags
  - kept `available=false` and `sync_supported=false` until endpoint implementations
- Capability tests updated in `backend/tests/test_connector_capabilities_endpoint.py`:
  - source matrix now includes `discord`, `zoom`, `teams`
  - env-driven `configured` assertions added for Discord/Zoom/Teams
- Frontend Sources panel update in `frontend/src/components/Sidebar.tsx`:
  - added explicit `setup` indicator for connectors with `configured=false`
- Ops docs updated:
  - `docs/planning/SMOKE_RUNBOOK.md` now includes Slack and Discord seeded sync scenarios
  - `docs/planning/RELEASE_HARDENING_CHECKLIST_S5.md` added
  - `backend/.env.example` includes Wave 2 readiness env placeholders
- Final verification after full Sprint 5 closure:
  - backend: `pytest -q` => 85 passed
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Sprint 6 completed (Zoom + Teams execution):

- New planning board: `docs/planning/SPRINT6_TASK_BOARD.md`
- Zoom integration delivered end-to-end:
  - connector: `backend/app/connectors/zoom_connector.py`
  - endpoint: `POST /api/v1/ingestion/connectors/zoom/sync`
  - tests: `backend/tests/test_zoom_connector.py`, `backend/tests/test_zoom_sync_endpoint.py`
- Teams integration delivered end-to-end:
  - connector: `backend/app/connectors/teams_connector.py`
  - endpoint: `POST /api/v1/ingestion/connectors/teams/sync`
  - tests: `backend/tests/test_teams_connector.py`, `backend/tests/test_teams_sync_endpoint.py`
- Capability matrix update:
  - `zoom` and `teams` switched to `available=true` and `sync_supported=true`
  - runtime `configured` flags remain env-driven
- Frontend source map update:
  - explicit visual styles for Zoom/Teams in `Sidebar`
  - setup indicator for `configured=false` still active
- Ops docs update:
  - `docs/planning/SMOKE_RUNBOOK.md` extended with Zoom/Teams sync scenarios
  - `docs/planning/RELEASE_HARDENING_CHECKLIST_S6.md` added
- Final verification after Sprint 6 closure:
  - backend: `pytest -q` => 91 passed
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Post-S6 reliability hardening (negative/retry tests):

- Zoom connector tests extended:
  - retry success path (transient failures recover within retry budget)
  - retry exhaustion path (error propagated after max attempts)
  - sync endpoint error-path persistence (`status=error` in connectors + error run in connector_runs)
- Teams connector tests extended with the same reliability/error-path coverage.
- Final backend verification after hardening:
  - backend: `pytest -q` => 97 passed

2026-07-01 — Retry policy hardening (HTTP-aware fail-fast):

- `BaseConnector.run_with_retry(...)` updated with HTTP-aware retry strategy:
  - retry on `429` and `5xx`
  - fail-fast on non-retryable `4xx` (for example `401`, `403`, `404`)
- Connector tests extended with provider status-code scenarios:
  - Zoom: no retry on `401`, retries on `429`
  - Teams: no retry on `401`, retries on `503`
- Updated backend verification after retry-policy hardening:
  - backend: `pytest -q` => 101 passed

2026-07-01 — Endpoint-level fail-fast contract for provider 401:

- API integration tests added for Zoom/Teams sync endpoints with monkeypatched provider fetch methods:
  - `/connectors/zoom/sync` returns `502` on provider `401` with fail-fast behavior (single attempt)
  - `/connectors/teams/sync` returns `502` on provider `401` with fail-fast behavior (single attempt)
- Both tests verify error persistence in connector registry and connector runs history.
- Updated backend verification after endpoint-level contract tests:
  - backend: `pytest -q` => 103 passed

2026-07-01 — Runtime retry controls for connector sync endpoints:

- All connector sync request models now support runtime retry overrides:
  - `retry_max_attempts` (1..10)
  - `retry_backoff_seconds` (0.0..5.0)
- Retry policy builder in ingestion API applies per-request overrides and passes `RetryPolicy` into all connector constructors.
- New integration test suite validates:
  - custom retry attempts/backoff are honored for Zoom and Teams sync paths
  - request validation boundaries return `422` for out-of-range retry options
- Updated backend verification after runtime retry-control rollout:
  - backend: `pytest -q` => 106 passed

2026-07-01 — Staging readiness pack (operational closure prep):

- Added staging protocol doc:
  - `docs/planning/STAGING_READINESS_PACK_S6.md`
- Added evidence capture template:
  - `docs/planning/STAGING_SMOKE_EVIDENCE_TEMPLATE.md`
- Added automation script for Wave 2 staging smoke run:
  - `backend/scripts/staging_smoke_wave2.ps1`
- This closes the documentation/automation gap for remaining pre-production validation tasks.

2026-07-01 — Staging evidence auto-validation:

- Added validator script for Wave 2 smoke output:
  - `backend/scripts/validate_staging_smoke_wave2.py`
- Added test coverage for validator rules:
  - `backend/tests/test_staging_smoke_validator.py`
- Validator checks cover:
  - mandatory check flags (`health`, `zoom_sync`, `teams_sync`, `connectors_registry`, `audit`, `stats`)
  - processed/inserted thresholds for Zoom/Teams
  - connectors registry status policy (`healthy`/`degraded`)
  - required audit actions for zoom/teams batch sync
- Updated backend verification after validator rollout:
  - backend: `pytest -q` => 110 passed

2026-07-01 — One-command Wave 2 release gate:

- Added orchestrator script:
  - `backend/scripts/release_gate_wave2.ps1`
- Script flow:
  - runs `staging_smoke_wave2.ps1`
  - runs `validate_staging_smoke_wave2.py`
  - emits `release_gate_wave2_report.json` and `release_gate_wave2_report.md`
  - returns process exit code aligned with GO/NO-GO decision

2026-07-01 — Security hardening follow-up (Project Review #2):

- Tenant binding hardened for JWT-authenticated callers:
  - `resolve_tenant_id(...)` now extracts tenant from JWT claims (`tenant_id` / `tenantId` / `tid`)
  - request/query tenant mismatch is rejected with `403`
  - JWT without tenant claim is rejected with `403`
- Permission dependencies hardened against wiring mistakes:
  - `require_connector_sync_permission(...)` and `require_ingestion_read_permission(...)` now call `require_api_key(...)` first
  - removes silent auth-bypass risk if these dependencies are reused on future routes
- Safer defaults applied:
  - `ALLINO_ALLOW_INSECURE_DEV` default switched to `false`
  - `docker-compose.yml` now sets `ALLINO_ENV=production` and `ALLINO_ALLOW_INSECURE_DEV=false`
  - `.env.example` updated accordingly
- Tests added/updated:
  - new API-level tenant binding tests: `backend/tests/test_tenant_binding_api.py`
  - JWT endpoint tests updated to include tenant claim where required
  - test harness stabilization in `backend/tests/conftest.py` for local test-mode defaults
- Updated backend verification after review-driven fixes:
  - backend: `pytest -q` => 115 passed

2026-07-01 — Rate limiting implemented (Project Review #2 follow-up):

- Added in-memory rate limiter module:
  - `backend/app/core/rate_limit.py`
- Added global middleware on backend app:
  - applies to `/api/v1/ingestion*` path family
  - returns `429` with `Retry-After` when threshold exceeded
- Added runtime config keys:
  - `ALLINO_RATE_LIMIT_ENABLED`
  - `ALLINO_RATE_LIMIT_REQUESTS`
  - `ALLINO_RATE_LIMIT_WINDOW_SECONDS`
- Added tests:
  - `backend/tests/test_rate_limiting.py`
- Updated environment/docs:
  - `backend/.env.example`
  - `docker-compose.yml`
- Updated backend verification after rate-limit rollout:
  - backend: `pytest -q` => 117 passed

2026-07-01 — Security headers implemented (Project Review #2 follow-up):

- Backend security headers middleware added:
  - `Content-Security-Policy`
  - `X-Content-Type-Options`
  - `X-Frame-Options`
  - `Referrer-Policy`
  - `Permissions-Policy`
  - `Strict-Transport-Security` for HTTPS requests
- Backend config/env support added:
  - `ALLINO_SECURITY_HEADERS_ENABLED`
  - `ALLINO_CSP_POLICY`
  - `ALLINO_HSTS_ENABLED`
  - `ALLINO_HSTS_MAX_AGE`
  - `ALLINO_HSTS_INCLUDE_SUBDOMAINS`
  - `ALLINO_HSTS_PRELOAD`
- Frontend runtime security headers added in `frontend/next.config.mjs`.
- Tests/build verification:
  - backend: `pytest -q` => 120 passed
  - frontend: `npm --prefix frontend run build` => success

2026-07-01 — Encryption at rest baseline implemented (Project Review #2 follow-up):

- Added field-level encryption module for sensitive persisted strings:
  - `backend/app/core/crypto.py` (Fernet-based, `enc:v1:` envelope)
- Startup validation:
  - production + encryption enabled requires `ALLINO_ENCRYPTION_KEY`
- Encrypted-at-rest repository fields:
  - `audit_logs.metadata`
  - `messages.preview`
  - `connectors.last_error`
  - `connector_runs.error`
- Env/runtime support added:
  - `ALLINO_ENCRYPTION_AT_REST_ENABLED`
  - `ALLINO_ENCRYPTION_KEY`
- Coverage:
  - `backend/tests/test_encryption_at_rest.py` verifies raw DB values are encrypted and read path is transparently decrypted
- Updated backend verification after encryption-at-rest rollout:
  - backend: `pytest -q` => 123 passed

2026-07-01 — Vault-backed secrets baseline implemented (Project Review #2 follow-up):

- Added secret resolver module:
  - `backend/app/core/secrets.py`
  - resolution order: environment variable first, Vault KV v2 fallback second
- Config/auth secret resolution now uses env-or-vault path for:
  - `ALLINO_API_KEY`
  - `ALLINO_JWT_SECRET`
  - `ALLINO_ENCRYPTION_KEY`
- Connector/capability secret checks now use env-or-vault path for provider tokens/channels.
- Added tests:
  - `backend/tests/test_vault_secrets.py`
  - `backend/tests/test_connector_capabilities_endpoint.py` (vault-backed configured case)
- Runtime env docs updated:
  - `backend/.env.example`
  - `docker-compose.yml`
- Updated backend verification after vault rollout:
  - backend: `pytest -q` => 127 passed

2026-07-01 — Connector token hardening and event-bus consumer baseline (Project Review #2 follow-up):

- Connector sync security cleanup:
  - removed body token fallback from connector sync payloads
  - connector token is accepted only via `X-Connector-Token` header
- Event-bus consumer baseline:
  - `backend/app/services/event_bus.py` adds async worker mode (`worker_async`) with dedicated in-process consumer thread
  - `process_connector_events(...)` supports worker path via `ALLINO_EVENT_BUS_ASYNC_CONSUMER_ENABLED`
  - timeout control: `ALLINO_EVENT_BUS_ASYNC_TIMEOUT_SECONDS`
  - retry control: `ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS`
  - worker metadata now includes `worker_attempts` and `queue_depth`, with fallback on exhausted retries
- External worker process baseline:
  - new worker entrypoint: `backend/app/workers/event_bus_worker.py`
  - shared batch processor extracted to `backend/app/services/ingestion_processor.py`
  - external-worker request/result path added behind `ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED`
  - external worker timeout control: `ALLINO_EVENT_BUS_EXTERNAL_WORKER_TIMEOUT_SECONDS`
  - external worker retry/backoff + DLQ controls:
    - `ALLINO_EVENT_BUS_EXTERNAL_WORKER_MAX_ATTEMPTS`
    - `ALLINO_EVENT_BUS_EXTERNAL_WORKER_BACKOFF_SECONDS`
    - `ALLINO_EVENT_BUS_EXTERNAL_WORKER_DLQ_STREAM`
  - external worker healthcheck mode: `python -m app.workers.event_bus_worker --healthcheck`
  - release gate supports strict external-worker validation (`-RequireExternalWorker`)
- Tests:
  - `backend/tests/test_event_bus.py` extended with async worker mode coverage
  - `backend/tests/test_event_bus_sync_response.py` updated for `worker_async` response mode
  - sync retry/fail-fast endpoint tests updated to header-only connector token contract
- Runtime docs/config updated:
  - `backend/.env.example`
  - `docker-compose.yml`
- Updated backend verification after these changes:
  - backend: `pytest -q` => 138 passed

2026-07-01 — External worker DLQ smoke gate (operations hardening):

- Added dedicated DLQ smoke script:
  - `backend/scripts/staging_smoke_external_worker_dlq.py`
- Release gate enhancements:
  - `backend/scripts/release_gate_wave2.ps1` supports strict DLQ mode via `-RequireExternalWorkerDlq`
  - strict mode runs DLQ smoke and includes its exit code/artifact path in release report
- External worker fault-injection toggle for controlled staging validation:
  - `ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX`
- Added tests:
  - `backend/tests/test_external_worker_dlq_smoke_script.py`
- Updated backend verification after DLQ gate integration:
  - backend: `pytest -q` => 140 passed

2026-07-01 — Release evidence/handoff tooling (undocumented at time of writing; backfilled):

- The following were implemented and wired into `release_gate_wave2.ps1` during the
  same session as the DLQ smoke gate above, but the changelog entry was never written
  before the session ended. Backfilling here so the handoff is accurate:
  - `backend/scripts/redact_release_artifacts.py` — strips secrets/tokens from
    release evidence files before they leave the machine.
  - `backend/scripts/build_release_evidence_bundle.py` — packages smoke output,
    validator report, and redacted artifacts into one evidence bundle.
  - `backend/scripts/generate_release_handoff_wave2.py` — generates a human-readable
    release handoff doc from the evidence bundle.
  - `backend/scripts/validate_release_gate_wave2_report.py` — validates the
    release gate JSON report structure/content independent of the gate script itself.
  - Tests: `test_release_artifacts_redaction.py`, `test_release_evidence_bundle.py`,
    `test_release_gate_report_validator.py`, `test_release_handoff_generator.py`.
- Verified backend: `pytest -q` => 151 passed (confirmed by re-running, matches
  actual test count; this file previously undercounted at 140).

2026-07-01 — Lint regression fix (post-session cleanup):

- `ruff check app tests --select F,E9` (the exact CI lint scope) was failing with
  6 unused-import errors left over from the security-hardening session:
  `ingestion.py` (`redact_secrets`), `slack_connector.py` (`os`),
  `test_ingestion_idempotency.py` (`UnifiedEvent`), and three config re-exports in
  `rate_limit.py` that are used cross-module via `rate_limit.X` attribute access
  (needed so `test_rate_limiting.py` can monkeypatch them) but look unused to a
  static import checker.
- Fix: removed the genuinely dead imports; added `# noqa: F401` + a comment on the
  three `rate_limit.py` re-exports explaining why they must stay.
- Verified: `ruff check app tests --select F,E9` => all checks passed;
  `pytest -q` => 151 passed; `npm --prefix frontend run build` => success.

2026-07-01 — Schema documentation (no code change):

- Added `backend/migrations/0009_deprecate_threads_users.sql` — a documentation-only
  no-op migration marking `threads` and `users` (from `0001_init.sql`) as not part
  of the active read/write path: thread grouping went to `messages.thread_key`
  instead (0007_thread_key.sql), and there is no user-record model backing auth
  (auth is env-based via `ALLINO_API_KEY`/`ALLINO_JWT_SECRET`). Tables are kept
  in place, not dropped — dropping tables is a destructive action and needs an
  explicit decision, not a silent cleanup.

Open items (as tracked before Sprint 7 — see resolution further down):

- No active sprint board beyond Sprint 6 (Wave 1 + Wave 2 connector coverage,
  JWT hardening, rate limiting, security headers, encryption at rest,
  Vault-backed secrets, and event-bus external worker + DLQ are all closed
  and verified against code, not just docs).
- `threads`/`users` tables documented as deprecated (see above) but not removed.
- Postgres + real Row-Level Security path still a commented-out template in
  `0002_rls.sql` — project remains SQLite-only.
- MFA for admin paths (CLAUDE.md §4) has no admin surface to apply to yet;
  not a gap in practice, but worth remembering once an admin UI exists.

2026-07-01 — Sprint 7 opened (S7-01 closed): JWT RS256 (asymmetric) support:

- New planning board: `docs/planning/SPRINT7_TASK_BOARD.md` — explicitly scoped to
  hardening/cleanup, not Wave 3 integrations.
- `PROJECT_MASTER_BRIEF.md` P0 item `BE-01` calls for `RS256 only`; the JWT path
  only supported HS256 (shared secret) verification. Since this service only
  ever verifies tokens issued by an external IdP (it never issues them), what
  was needed is public-key verification, not a private key here.
- `core/config.py` adds `ALLINO_JWT_PUBLIC_KEY` (PEM, `\n`-escaped single-line
  values supported).
- `core/security.py` adds `_jwt_verification_key()`: picks `ALLINO_JWT_PUBLIC_KEY`
  for asymmetric algorithms (`RS*`/`ES*`/`PS*`) or `ALLINO_JWT_SECRET` for `HS*`,
  used consistently everywhere the code previously checked `ALLINO_JWT_SECRET`
  as a truthy gate (`require_api_key`, `require_connector_sync_permission`,
  `require_ingestion_read_permission`, `get_authenticated_jwt_payload`).
  Existing HS256 deployments are unaffected — no config migration needed.
- Tests added: valid RS256 token accepted, RS256 token signed by the wrong
  private key rejected, RS256 configured without a public key fails closed
  (503, consistent with existing fail-closed policy), RS256 role/scope claims
  respected by the connector-sync permission dependency.
- `.env.example` documents both the symmetric and asymmetric JWT configuration
  paths side by side.
- Verified: `pytest -q` => 155 passed; `ruff check app tests --select F,E9` =>
  all checks passed.

2026-07-01 — S7-02 and S7-03 explicitly deferred (user decision):

- Asked the user directly (plain-language, not jargon) what to do about the two
  remaining Sprint 7 items. User picked the conservative option for both:
  - S7-02 (Postgres + real Row-Level Security): **not needed now**. Trigger to
    revisit: when a real multi-tenant production deployment with untrusted
    tenants is actually being planned. Don't start this speculatively — it's
    genuine new infrastructure (Postgres, connection pooling, migration
    tooling, RLS policies, re-testing every repository) not a drop-in change.
  - S7-03 (`threads`/`users` tables): **leave as-is**. Stay documented as
    deprecated (`0009_deprecate_threads_users.sql`), not dropped. Revisit only
    if a real feature needs a user-record model or a real thread-table shape.
- Sprint 7 is closed with this outcome: S7-01 shipped, S7-02/S7-03 consciously
  deferred with a stated trigger condition, not silently dropped.

2026-07-01 — S7-04: Security Center + Settings (core shell completion) + a
production-breaking CSP bug found and fixed while verifying it in a browser:

- CLAUDE.md §6 requires 5 core shell views: Inbox, Focus, Incident, Security
  Center, Settings. Only the first three existed — "Security Center" and
  "Settings" were nav buttons in `Sidebar.tsx` with no `onClick` handling for
  those ids (same dead-button pattern that was previously fixed for
  Focus/Incident mode in an earlier session). Fixed:
  - `Mode` type moved to `lib/types.ts` (was duplicated locally in both
    `page.tsx` and `Sidebar.tsx`) and now includes `"security" | "settings"`.
  - New `components/SecurityCenter.tsx`: self-fetching (only loads data when
    actually mounted), renders the tenant-scoped audit log via a new
    `fetchAudit()` in `lib/api.ts` hitting the existing (already-tested)
    `GET /api/v1/ingestion/audit` endpoint — this endpoint had zero frontend
    consumers before this change. Has loading/error-with-retry/empty states
    per the mandatory-states rule in CLAUDE.md §6.
  - New `components/SettingsPanel.tsx`: read-only view of tenant id, backend
    URL, and per-connector configuration status (reusing the capabilities
    data already polled in `page.tsx`). Deliberately no editable secrets —
    those stay environment/Vault-only per the security model.
  - `app/page.tsx` branches the main content area on `mode` to render these
    as full views instead of the 3-pane inbox layout.
- **While verifying this in an actual browser** (not just `npm run build`,
  which doesn't execute the page) found that the frontend's CSP — added in an
  earlier session's security-headers work — was `default-src 'self'` with
  nothing else. That blocks the Google Fonts stylesheet, blocks every
  `style={{...}}` inline style (the pattern used by literally every component
  in this app), blocks Next.js's own inline runtime scripts, and blocks
  `fetch()` calls to the cross-origin backend. It looks like the same policy
  string was copied from the backend's JSON-API CSP without checking whether
  it works for an actual HTML page. This was not caught by `next build`
  (compiles fine) or by any existing test — only by loading the page and
  reading the console.
  - Fixed in `frontend/next.config.mjs`: added `style-src 'self' 'unsafe-inline'
    https://fonts.googleapis.com`, `font-src 'self' https://fonts.gstatic.com`,
    `img-src 'self' data:`, `script-src 'self' 'unsafe-inline'` (plus
    `'unsafe-eval'` only in dev mode, for Fast Refresh), and `connect-src 'self'
    <backend origin, derived from NEXT_PUBLIC_BACKEND_URL>`.
  - Verified end-to-end in a real browser (dev server, real backend, seeded
    data): zero console errors, Inbox/Focus/Incident/Security Center/Settings
    all render and fetch correctly, no CSP violations.
- Verified: `pytest -q` => 155 passed (unchanged, backend untouched);
  `tsc --noEmit` clean; `npm run build` => success; manual browser check via
  Playwright MCP tools (network + console) with a real backend instance.

2026-07-01 — Sprint 8 opened and closed (S8-01): sanitized error responses (BE-09):

- New planning board: `docs/planning/SPRINT8_TASK_BOARD.md` — scoped to the one remaining applicable
  P1 security-baseline item not yet on any board (`PROJECT_MASTER_BRIEF.md` §4, `BE-09`); infra-only P1/P2
  items (WAF, SIEM, mTLS mesh, DDoS protection, DNSSEC) explicitly excluded — not applicable to this
  local-first single-service architecture without a separate decision to build that infrastructure.
- `backend/app/main.py` adds a global `Exception` handler:
  - generates a UUID `error_id` per unhandled exception
  - logs full exception detail + `error_id` server-side via `logging.exception(...)`
  - returns a generic `{"detail": "Internal server error", "error_id": "..."}` body with `500`, no
    stack trace or exception internals in the client-visible response
  - existing `HTTPException` raises (all endpoints) are unaffected — Starlette resolves the
    already-registered `HTTPException` handler before falling back to the new `Exception` handler
- Tests added: `backend/tests/test_sanitized_error_responses.py`
  - unhandled exception (injected via monkeypatch) returns sanitized body with `error_id`, no leaked
    secret/exception-type/traceback text
  - existing `HTTPException` path (invalid cursor) still returns its specific status/detail unchanged
- Verified: `pytest -q` => 157 passed; `ruff check app tests --select F,E9` => all checks passed.

2026-07-01 — Sprint 9 opened and closed (S9-01): dependency vulnerability remediation + SCA CI gate (OP-04):

- New planning board: `docs/planning/SPRINT9_TASK_BOARD.md`. A `pip-audit` dry-run (done while preparing
  the OP-04 CI/CD security-gate item) found 25 known CVEs across `pyjwt==2.9.0`, `cryptography==43.0.3`,
  and `starlette==0.38.6` (transitive via `fastapi==0.115.0`) — PyJWT sits directly under this app's
  entire auth model, so the user was asked how to handle it rather than silently deciding; chose full
  remediation before adding the CI gate.
- Backend (`backend/requirements.txt`): `fastapi` 0.115.0 -> 0.138.2, `uvicorn[standard]` 0.30.6 ->
  0.49.0, `pydantic` 2.9.2 -> 2.13.4, `httpx` 0.27.2 -> 0.28.1, `PyJWT` 2.9.0 -> 2.13.0, `redis` 5.1.1 ->
  8.0.1, `cryptography` 43.0.3 -> 49.0.0. `backend/requirements-dev.txt` adds `pip-audit==2.10.1`.
  Full `pytest -q` suite (157 tests, including JWT RS256/HS256 auth and encryption-at-rest paths) passes
  unchanged after the bump; `pip-audit -r backend/requirements.txt` -> no known vulnerabilities.
- Frontend (`frontend/package.json`): `npm audit` additionally found `next@14.2.25` itself carried a
  high-severity advisory set (SSRF, cache poisoning, DoS, XSS — see advisory list in the npm audit
  output), and fixing the transitive `postcss` moderate finding required a `next` major bump anyway
  (`next`'s own dependency pin on `postcss<8.5.10` only lifts in newer `next` releases). Bumped `next`
  14.2.25 -> 16.2.9, `react`/`react-dom` 18.2.0 -> 18.3.1 (stayed on React 18 — Next 16's peer range
  accepts `^18.2.0`, so this avoided a React 19 migration entirely since the app has no React
  19-dependent code). Added `"overrides": { "postcss": "8.5.16" }` to force the last transitive
  moderate finding (bundled inside `next`) to a patched version. `npm audit` -> 0 vulnerabilities.
  `tsc --noEmit` clean (Next's build step auto-updated `tsconfig.json`: added `.next/dev/types/**/*.ts`
  to `include`, set `jsx` to `react-jsx` — both standard, non-breaking for this Turbopack/App-Router
  setup). `npm run build` -> success.
- Verified live in a real browser (not just `next build`) per the CLAUDE.md §6 UI-verification rule,
  since this is a major frontend framework version bump: ran the app in **production mode**
  (`next build && next start`) against a real seeded backend — Inbox (40 items), source filters,
  Security Center (audit log), and Settings all render correctly with zero console errors. Note: an
  earlier attempt to verify against the **dev server** (`next dev`, Turbopack + HMR) got stuck on
  "Syncing sources…" indefinitely in this sandbox's browser-automation environment; root-caused to the
  dev-mode HMR WebSocket repeatedly failing its handshake through this sandbox's docker network bridge
  (`host.docker.internal`), not to the dependency upgrade itself — confirmed by reproducing the same
  hang with `reactStrictMode` toggled off (ruled out a React-effect-double-invoke theory) and then
  confirming clean, complete data loads in production mode (no HMR involved) on the identical upgraded
  build. Do not read too much into a stuck "Syncing sources…" during *dev-server* verification in a
  containerized/sandboxed browser tool specifically — verify via `next build && next start` if it
  recurs, before assuming an app-code regression.
- CI gates added:
  - `.github/workflows/backend-ci.yml`: new `pip-audit -r backend/requirements.txt` step (fails build on
    any finding).
  - `.github/workflows/frontend-ci.yml`: new `npm audit --audit-level=high --prefix frontend` step.
- Infra-only P1/P2 items from `PROJECT_MASTER_BRIEF.md` §4 (WAF, SIEM, mTLS service mesh, DDoS
  protection, DNSSEC) remain explicitly out of scope — not applicable to this local-first, single
  backend-service architecture without a separate decision to build that infrastructure.

2026-07-01 — Sprint 10 opened and closed (S10-01, S10-02): Generic HTTP Connector + Webhook Receiver:

- New planning board: `docs/planning/SPRINT10_TASK_BOARD.md`. `CLAUDE.md` §5 documented an "Extensible
  Connector Architecture" decision on 2026-06-30 (Generic HTTP Connector + Webhook Receiver, so a new
  source = registering a connector, not writing Python code) but it had never been implemented — verified
  by grep before starting, zero hits for "webhook"/"generic" in `backend/app`. Found while reviewing
  overall project status and surfaced to the user as a real architectural gap; user picked it as the
  Sprint 10 priority over Wave 3 integrations and reply/write-back.
- New migration `0010_generic_connectors.sql`: `generic_connector_configs` table (id = UUID used
  directly as the webhook path segment, tenant_id, name, slug, base_url, auth_method, auth_header_name,
  poll_interval_seconds, field_mapping as JSON, webhook_enabled, status). No secret columns — by design,
  matching `CLAUDE.md` §4 (secrets via env/Vault only, never in the DB).
- `backend/app/connectors/generic_http_connector.py`: `GenericHttpConnector(BaseConnector)` — same
  `start/stop/health/fetch_events` contract as the other 9 connectors, reuses `RetryPolicy`/
  `run_with_retry`. `extract_path()` does dot-path nested-dict extraction (no array indices — MVP).
  `extract_items_from_payload()` normalizes a response into a flat item list — accepts a bare JSON array,
  or `{"items"|"data"|"results": [...]}`, or falls back to treating a single object as one item; shared
  between the poll path and the webhook path so both parse response shapes identically.
  `map_generic_item_to_unified_event()` builds the UnifiedEvent-shape dict from configured
  externalId/timestamp/preview paths.
  Auth/webhook secrets resolve via `core/secrets.py` using a name derived from the slug:
  `ALLINO_GENERIC_{SLUG}_TOKEN` / `ALLINO_GENERIC_{SLUG}_WEBHOOK_SECRET` (slug uppercased, `-` replaced
  with `_` via `slug_to_env_key()` — plain `slug.upper()` would have produced an invalid POSIX env var
  name for hyphenated slugs, caught before shipping).
- `backend/app/db/repositories/generic_connectors_repo.py`: CRUD for the config table (create scoped to
  tenant, list/get/delete all tenant-scoped except the webhook lookup path, which looks up by id alone
  since an external caller can't supply a tenant header).
- `backend/app/api/generic_connectors.py` — two routers:
  - Management router at `/api/v1/ingestion/connectors/generic` (create/list/sync/delete), tenant-scoped
    via `resolve_tenant_id`, protected by the existing `require_connector_sync_permission` (write ops) /
    `require_ingestion_read_permission` (list) dependencies — no new permission tier introduced.
  - `webhook_router`: `POST /webhooks/{connector_id}` — deliberately outside the ingestion router's
    `require_api_key` dependency (an external service pushing events doesn't have our credentials);
    identity and trust come from HMAC instead. `X-Webhook-Signature: sha256=<hex>` computed over the raw
    request body; verified with `hmac.compare_digest`. Fail-closed: `webhook_enabled=true` but no secret
    configured -> `503`; missing/invalid signature -> `401`; unknown connector id or `webhook_enabled=false`
    -> `404` for both cases uniformly (avoids leaking which ids exist).
  - Both the manual-sync and webhook-receive paths route through the same `process_connector_events` +
    `process_connector_batch` pipeline the other 9 connectors use — same dedup, normalization, audit
    logging, and event-bus path. A poll-sync and a webhook delivery of the same `externalId` correctly
    dedupe against each other (covered by test).
- `backend/app/core/rate_limit.py`: `is_rate_limited_path()` now also matches `/webhooks`, since it's a
  new public-ish ingestion-adjacent endpoint.
- `backend/app/main.py`: registers both new routers; `CORSMiddleware.allow_methods` gains `DELETE` (the
  new delete-config endpoint).
- `backend/.env.example` documents the `ALLINO_GENERIC_{SLUG}_TOKEN` / `..._WEBHOOK_SECRET` pattern with
  a worked example.
- Tests added: `test_generic_http_connector.py` (path extraction, payload-envelope variants, mapping,
  connector lifecycle), `test_generic_connector_endpoints.py` (CRUD, tenant isolation, duplicate-slug
  409, api_key-without-header 422, sync success, sync failure updates registry to `error`, sync against
  unknown id -> 404), `test_generic_connector_webhook.py` (missing-secret 503, invalid/missing signature
  401, valid signature single-object and array-batch payloads, unknown/disabled webhook 404, dedup against
  a prior poll sync).
- Verified: backend `pytest -q` => 179 passed; `ruff check app tests --select F,E9` => all checks passed;
  `pip-audit -r backend/requirements.txt` => no known vulnerabilities.
- Explicitly out of scope for this sprint (see board): frontend UI for managing generic connectors
  (CLAUDE.md §5 only requires "via UI or API" — API is sufficient for MVP); an internal polling scheduler
  for `poll_interval_seconds` (the project has no auto-poll for any of its 9 existing connectors either —
  sync is on-demand via the `/sync` endpoint everywhere, so this isn't a regression, just an existing
  pattern extended consistently).

2026-07-01 — Sprint 11 opened and closed (S11-01, S11-02): reply / write-back MVP (Telegram + Slack):

- New planning board: `docs/planning/SPRINT11_TASK_BOARD.md`. `PROJECT_MASTER_BRIEF.md`: reply/action
  functionality was deliberately deferred until after the security gate — the gate is now largely
  closed (Sprint 1-9), and the app was still 100% read-only (confirmed by grep: zero hits for
  "reply"/"send_message"/"outbound" in `backend/app`; the frontend had only a static, non-functional
  "Reply securely…" composer placeholder in `ThreadPanel.tsx`). User picked this as the Sprint 11
  priority.
- Scope decision: MVP covers only Telegram and Slack, not all 9 connector sources. Both have a simple
  bot-token send API (no OAuth flow) and — critically — `messages.external_id` already contains
  everything needed to address a reply (Telegram: `chat_id:message_id`; Slack: `channel:ts`) without
  persisting the raw ingestion payload, which the `messages` table deliberately never stores (only
  `preview`/`thread_key`/`priority` survive normalization). GitHub/GitLab/Jira/Linear "replies" are
  issue/PR comments — a different data model entirely — explicitly out of scope, separate task if
  needed.
- New migration `0011_outbound_replies.sql`: `outbound_replies` table (id, tenant_id, event_id, source,
  external_id, text [encrypted], status, error [encrypted], created_at) — operational history of every
  reply attempt, same pattern as `connector_runs`.
- `backend/app/db/repositories/messages_repo.py` adds `get_message(tenant_id, event_id)` — a point
  lookup; previously only listing existed.
- `backend/app/connectors/telegram_connector.py` adds `send_telegram_reply()` (Bot API `sendMessage`,
  parses `chat_id:message_id`, sets `reply_to_message_id` when present).
  `backend/app/connectors/slack_connector.py` adds `send_slack_reply()` (Web API `chat.postMessage`,
  parses `channel:ts`, sets `thread_ts` to reply in-thread). Both reuse the existing
  `ALLINO_TELEGRAM_BOT_TOKEN` / `ALLINO_SLACK_BOT_TOKEN` secrets already used for the poll path — no
  new secrets introduced.
- New permission tier: `core/config.py` adds `ALLINO_JWT_REPLY_ROLES` (default `admin,operator`) /
  `ALLINO_JWT_REPLY_SCOPES` (default `messages:reply,reply:send`); `core/security.py` adds
  `require_reply_permission()`, same shape as the existing sync/read tiers.
- New router `backend/app/api/replies.py`:
  - `POST /api/v1/ingestion/messages/{event_id}/reply` — tenant-scoped via `get_message`. `404` unknown
    message, `400` unsupported source, `503` fail-closed when the provider bot token isn't configured
    (checked before any delivery attempt — intentionally *not* audit-logged, since nothing was
    attempted yet; matches the existing fail-closed-503 pattern elsewhere in the codebase), `502` on
    delivery failure. Every actual delivery attempt (success or failure) is recorded in both
    `outbound_replies` and the append-only `audit_logs` (`message.reply.sent` / `message.reply.failed`).
  - `GET /api/v1/ingestion/replies` — tenant-scoped operational history, same shape as
    `connector_runs`.
- Frontend (`ThreadPanel.tsx`, `lib/api.ts`, `lib/types.ts`): the static composer placeholder is now a
  real controlled `<textarea>` wired to a new `sendReply()` call. The composer only renders for
  `REPLY_SUPPORTED_SOURCES` (`telegram`, `slack`); other sources show an honest disabled explanation
  instead of a fake always-on composer. Loading/error/success states added (CLAUDE.md §6 mandatory
  states rule). The pre-existing "End-to-end encrypted" badge was **factually wrong** (the app does
  HTTPS transport + backend-mediated relay to the provider API, not E2E encryption of message content)
  — replaced with "Encrypted in transit (TLS)", a security-first correction, not a style change.
- **Found and fixed while doing the mandatory live-browser verification (not originally in scope,
  same pattern as the Sprint 7 CSP catch):** `frontend/src/app/page.tsx`'s `mode`/`filters` `useState`
  initializers read `sessionStorage` synchronously. For a returning visitor with a persisted non-default
  value (e.g. `mode: "settings"` from an earlier tab session), this produced a React hydration error
  #418 — SSR always renders the default, the client's first paint (which hydration must match) read the
  persisted value instead. `next build`/`tsc` didn't catch it (only visible as a runtime console error in
  a real browser). Fixed: both `useState` calls now always start from the SSR-safe default; a new
  mount-only `useEffect` restores persisted mode/filters *after* hydration. Getting this right also
  required a `restoringFromStorageRef` guard so the existing "mode changed → reset filters" effect
  doesn't clobber filters that were just restored from storage (traced through manually, see the code
  comments). Verified by reproducing with `sessionStorage.setItem('allino.mode','settings')` before
  reload (error present before fix, gone after) and confirming the mode still actually restores
  correctly (not just that the error went away).
- Tests added: `backend/tests/test_reply_delivery.py` (external_id parsing, request shape,
  success/API-error paths for both `send_telegram_reply`/`send_slack_reply`, mocking `httpx.Client.post`
  since these are plain functions, not connector-lifecycle methods), `backend/tests/test_reply_endpoint.py`
  (404/400/503/502 paths, tenant isolation, success records both audit log and `outbound_replies`
  history, failure records the error).
- Verified: backend `pytest -q` => 191 passed; `ruff check app tests --select F,E9` => all checks
  passed; `pip-audit -r backend/requirements.txt` => no known vulnerabilities. Frontend: `tsc --noEmit`
  clean; `npm run build` => success; `npm audit` => 0 vulnerabilities; live browser verification
  (production build, real seeded Telegram message) — composer renders for Telegram, sends a real
  request, correctly displays the fail-closed 503 error text, disabled state renders correctly for a
  GitHub-sourced item, zero unexpected console errors (only the expected/intentional 503 HTTP log for
  the deliberately-unconfigured-token test scenario).
- Explicitly out of scope (see board): reply support for the other 7 connector sources; auto-reingesting
  a sent reply as a new inbox message (not required for MVP).

2026-07-01 — Sprint 12 opened and closed (S12-01): Google Calendar/Meet connector (Wave 1 Optional):

- New planning board: `docs/planning/SPRINT12_TASK_BOARD.md`. `PROJECT_MASTER_BRIEF.md` §C and
  `CLAUDE.md` §3 both list Google Calendar/Meet under Wave 1 Optional — the one Wave 1 connector
  never implemented (confirmed by grep before starting: zero hits for "google"/"calendar" in
  `backend/app`). No open Sprint 12 board existed and this was picked as the next scoped, reversible
  unit of work rather than starting Wave 3 (still explicitly blocked per the Sprint 11 guardrail note)
  or a new architecture change.
- Scope decision: REST-polling connector baseline only, matching the on-demand-sync pattern every
  other connector already uses. The "auto-renew watch channels" (push API, 7-day channel expiry
  needing a renewal cron) needs new scheduler infrastructure this project doesn't have for any
  connector yet — explicitly deferred as a future hardening item (`PROJECT_MASTER_BRIEF.md` §C already
  earmarks Google Calendar hardening as a separate Wave 2 line), not silently dropped. See the Sprint 12
  board for the full reasoning.
- `backend/app/connectors/google_calendar_connector.py`: `GoogleCalendarConnector` on the standard
  `BaseConnector` contract (start/stop/health/fetch_events), reuses `RetryPolicy`/`run_with_retry`
  (429/5xx retry, 4xx fail-fast comes for free). Auth via `ALLINO_GOOGLE_CALENDAR_TOKEN` — a pre-issued
  OAuth2 access token resolved via the existing env/Vault secrets path, same simplification already
  used for Zoom/Teams (no in-app OAuth refresh flow). Maps Calendar Events API `items[]` to
  UnifiedEvent, resolving a Meet URL from `conferenceData.entryPoints` (preferring the `video` entry
  point) with a fallback to the legacy `hangoutLink`; cancelled events get a `[Cancelled]` preview
  prefix.
- New endpoint `POST /api/v1/ingestion/connectors/google_calendar/sync` reuses the shared
  `_run_connector_sync(...)` helper — telemetry, connector-registry upsert, run history, event-bus
  routing, and audit logging all come for free. Capability matrix and `frontend/src/components/Sidebar.tsx`
  source map updated with a `google_calendar` entry.
- Tests: `backend/tests/test_google_calendar_connector.py`, `backend/tests/test_google_calendar_sync_endpoint.py`,
  `test_connector_capabilities_endpoint.py` extended.
- Verified: backend `pytest -q` => 202 passed; `ruff check app tests --select F,E9` => all checks
  passed. Frontend: `tsc --noEmit` clean; `npm run build` => success. Live browser verification
  (production build, real backend, two seeded events — one confirmed, one cancelled): Sources panel
  shows `google_calendar` healthy with telemetry, Connector Operations/Recent Runs show the sync, inbox
  filter bar gets a `google_calendar` chip, both events render correctly (cancelled one flagged
  high-priority), thread panel opens and honestly states replies aren't supported for this source
  (deliberately not added to `REPLY_SUPPORTED_SOURCES` — a calendar event has no reply semantics).
  Zero unexpected console errors. Note for future sessions verifying live in this sandbox: the
  browser tool runs in a container that can't resolve `localhost` back to the host — point
  `NEXT_PUBLIC_BACKEND_URL` at `http://host.docker.internal:8000`, bind uvicorn with
  `--host 0.0.0.0`, add the matching origin to `ALLINO_ALLOWED_ORIGINS`, rebuild, and **check for a
  stale process still holding the old port/config** (`netstat -ano` showed two processes bound to the
  same port after an ineffective `pkill` in this session — `pkill -f uvicorn`/`next-server` did not
  reliably kill the Windows-native child processes from this shell; use `taskkill //PID <pid> //F`
  found via `netstat -ano | grep LISTENING` instead). Revert the env var afterward — it's a local-only
  dev convenience, not a real config change.

2026-07-02 — Sprint 13 opened and closed (S13-01): Generic HTTP Connector management UI:

- New planning board: `docs/planning/SPRINT13_TASK_BOARD.md`. Closes a gap
  flagged as deliberate/known since Sprint 10 (`CLAUDE.md` §5): the Generic
  HTTP Connector + Webhook Receiver architecture shipped API-only, with no
  frontend for managing configs. Picked over Wave 3 (still explicitly
  blocked without its own board), Google Calendar push/watch-channel renewal
  (needs new scheduler infra), and reply/write-back for the remaining 8
  connector sources (needs a per-connector data-model decision) because it's
  pure frontend work on top of an already-implemented, already-tested backend
  API — no new infrastructure, no new security surface.
- New frontend types in `frontend/src/lib/types.ts`: `GenericConnectorConfig`,
  `GenericConnectorCreateInput`, `GenericConnectorFieldMapping`,
  `GenericConnectorAuthMethod`.
- New API client functions in `frontend/src/lib/api.ts`:
  `fetchGenericConnectors`, `createGenericConnector`,
  `deleteGenericConnector` — hitting the existing Sprint 10 endpoints
  (`GET/POST /api/v1/ingestion/connectors/generic`,
  `DELETE /api/v1/ingestion/connectors/generic/{id}`). Deliberately no manual
  "sync now" trigger: none of the 10 built-in connectors expose one from the
  frontend either (sync is externally triggered — cron/staging scripts — for
  all of them), so adding one here would be a new UX pattern, not a
  consistent one; kept out of scope for this board.
- New component `frontend/src/components/GenericConnectorsPanel.tsx`:
  self-fetching list + collapsible create form (name, base URL, auth method
  with conditional auth-header-name field, poll interval, field mapping
  externalId/timestamp/preview, webhook toggle) + delete per row + webhook
  URL display when enabled. Loading/error-with-retry/empty states per the
  mandatory-states rule in `CLAUDE.md` §6. Coded against existing CSS custom
  properties only, matching the style of `SecurityCenter.tsx`/
  `SettingsPanel.tsx` (no hardcoded colors/radii). Wired into
  `SettingsPanel.tsx` below the existing "Connected Sources" card.
- Verified: backend `pytest -q` => 202 passed (unchanged — no backend code
  touched this sprint, Sprint 10 already shipped and tested the API).
  Frontend: `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification (real backend + real frontend, sandboxed browser
  tool via `host.docker.internal:8000`, per the standing sandbox note below):
  empty state renders correctly, create form's conditional auth-header field
  only appears for API-key auth, client-side validation blocks submission
  with a missing required header name, a full create (name/base URL/api_key
  auth+header/field mapping/webhook enabled) succeeds and the list shows
  name/slug/auth method/base URL/webhook URL, delete removes it and restores
  the empty state. Zero unexpected console errors (only the pre-existing,
  unrelated favicon 404). Frontend rebuilt afterward without the sandbox-only
  backend URL override before ending the session.
- Explicitly out of scope (see board): editing an existing config (no
  backend `PATCH`/`PUT` endpoint exists yet — separate unit of work); manual
  sync trigger from the UI; webhook secret management from the UI (stays
  env/Vault-only, same security model as every other connector secret).

2026-07-02 — Sprint 14 opened and closed (S14-01): Rocket.Chat connector (Wave 3 start):

- New planning board: `docs/planning/SPRINT14_TASK_BOARD.md`. `CLAUDE.md` §3
  lists Wave 3 as Rocket.Chat/WhatsApp Business/Viber — the only integration
  wave never started (confirmed by grep before starting: zero hits for
  "rocket"/"viber"/"whatsapp" in `backend/app`). Every prior sprint board
  since Sprint 11 carried a guardrail telling future agents not to start
  Wave 3 without opening a board first; this board is that decision, made
  under the user's standing "choose the next scoped/reversible unit of work
  yourself" delegation. Scoped to **one** connector, not all three — the
  three Wave 3 sources don't share an auth/data shape the way Zoom+Teams did
  in Sprint 6, so bundling them increases risk for no benefit. Rocket.Chat
  was picked because it's a self-hosted REST API closest to patterns already
  in this codebase (GitLab's configurable `base_url`, Discord's chat-message
  mapping shape); WhatsApp Business (Meta Graph API, phone-number addressing,
  mandatory webhook signatures) and Viber (proprietary bot API) are left for
  their own future sprints.
- New connector: `backend/app/connectors/rocketchat_connector.py`.
  `RocketChatConnector` on the standard `BaseConnector` contract (start/stop/
  health/fetch_events, `RetryPolicy`/`run_with_retry` reuse — 429/5xx retry,
  4xx fail-fast for free, same as all 10 other connectors). Auth is a
  *pair* of secrets — `ALLINO_ROCKETCHAT_TOKEN` + `ALLINO_ROCKETCHAT_USER_ID`
  (Rocket.Chat's REST API requires both `X-Auth-Token` and `X-User-Id`
  headers, unlike the single-bearer-token connectors already in this
  codebase) — plus `ALLINO_ROCKETCHAT_BASE_URL` (no universal default, always
  self-hosted) and `ALLINO_ROCKETCHAT_CHANNEL_ID`, all resolved via the
  existing env/Vault secrets path. Maps
  `GET {base_url}/api/v1/channels.messages?roomId=...` response `messages[]`
  to UnifiedEvent using the same chat-message shape as Discord.
- New sync endpoint: `POST /api/v1/ingestion/connectors/rocketchat/sync`
  (tenant-scoped, `require_connector_sync_permission`, optional
  `channel_id`/`base_url` overrides), reusing the shared
  `_run_connector_sync(...)` helper — telemetry, connector-registry upsert,
  run history, event-bus routing, and audit logging all come for free.
  Capability matrix and frontend `Sidebar.tsx` source map updated with a
  `rocketchat` entry, following the exact pattern of every prior connector
  addition.
- Tests: `backend/tests/test_rocketchat_connector.py` (mapping, seeded
  fetch, degraded-without-credentials health check, retry success/
  exhaustion, 401 fail-fast, 429 retry), `backend/tests/test_rocketchat_sync_endpoint.py`
  (seeded ingest, error-path persistence, 401 fail-fast at the endpoint
  level). `test_connector_capabilities_endpoint.py` extended for the new
  source.
- Verified: backend `pytest -q` => 213 passed (up from 202);
  `ruff check app tests --select F,E9` => all checks passed. Frontend:
  `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification (real backend + real frontend, sandboxed browser
  tool via `host.docker.internal:8000`, per the standing sandbox note
  below): seeded two Rocket.Chat messages via the sync endpoint, confirmed
  the Sources panel/Connector Operations/Recent Runs all show the healthy
  sync, the inbox filter bar gets a `rocketchat` chip, both messages render
  correctly, opening a thread shows the correct fallback source badge (not
  in `ThreadPanel`'s `SOURCE_MAP`, same as every Wave 2/Google Calendar
  source) and an honest "Replies aren't supported for rocketchat yet"
  composer state (deliberately not added to `REPLY_SUPPORTED_SOURCES`).
  Zero unexpected console errors. Frontend rebuilt afterward without the
  sandbox-only backend URL override before ending the session.
- Explicitly out of scope (see board): WhatsApp Business and Viber (separate
  future sprints); reply/write-back for `rocketchat`; manual sync trigger
  from the UI.

2026-07-02 — Sprint 15 opened and closed (S15-01): reply support extended to Discord and Rocket.Chat:

- New planning board: `docs/planning/SPRINT15_TASK_BOARD.md`. Continuing
  under the user's "continue what you can without me" delegation. Explicitly
  did **not** start WhatsApp Business/Viber (both are webhook-push-only APIs
  with no message-list/poll endpoint — building either means a new built-in
  webhook-receiver connector shape, a real architecture decision, not a
  same-pattern addition) or Google Calendar push/renewal (needs scheduler
  infra). Picked reply extension instead: Sprint 11 scoped reply to
  Telegram+Slack "for MVP," not because Discord/Rocket.Chat were
  incompatible — both are chat-message-shaped exactly like Telegram/Slack
  (bot-token message-post API, `channel:message_id`-style `external_id`
  already in place from their connector mapping functions), making this a
  same-pattern extension of an existing feature rather than new
  architecture — the safest kind of unsupervised continuation.
- `backend/app/connectors/discord_connector.py` adds `send_discord_reply()`
  (Discord REST `POST /channels/{channel_id}/messages`, `Bot {token}` auth,
  sets `message_reference.message_id` for in-context replies).
- `backend/app/connectors/rocketchat_connector.py` adds
  `send_rocketchat_reply()` (REST `POST /api/v1/chat.postMessage`,
  `X-Auth-Token`/`X-User-Id` headers). Rocket.Chat is the only reply source
  needing 2 extra config values beyond the token
  (`ALLINO_ROCKETCHAT_USER_ID`, `ALLINO_ROCKETCHAT_BASE_URL`) — added a
  small `_REPLY_EXTRA_CONFIG_ENV_KEYS` dict in `replies.py` (currently just
  this one entry) checked alongside the token so missing config fails
  closed with 503, not a spurious 502 delivery-failure record.
- `backend/app/api/replies.py`: `_REPLY_TOKEN_ENV_KEYS`/`_REPLY_SENDERS`
  extended with `discord`/`rocketchat`.
  `frontend/src/lib/types.ts`: `REPLY_SUPPORTED_SOURCES` now
  `["telegram", "slack", "discord", "rocketchat"]` — no other frontend
  change needed, `ThreadPanel.tsx`'s composer already keys off this constant.
- Tests: `backend/tests/test_reply_delivery.py` extended with
  `send_discord_reply`/`send_rocketchat_reply` unit tests (request shape,
  missing-channel `ValueError`, API-error `RuntimeError`, missing-user-id
  `RuntimeError` for Rocket.Chat). `backend/tests/test_reply_endpoint.py`
  extended with a Rocket.Chat-specific 503 case (token present, extra config
  missing) and a full success-path case.
- Verified: backend `pytest -q` => 222 passed (up from 213);
  `ruff check app tests --select F,E9` => all checks passed. Frontend:
  `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification (real backend + real frontend, sandboxed browser
  tool via `host.docker.internal:8000`): seeded one Discord and one
  Rocket.Chat message via their sync endpoints, confirmed the reply composer
  now renders (was "not supported" before) for both, and that sending a
  reply with no bot token configured correctly surfaces the fail-closed 503
  "Reply is not configured for source '...'" for both — the Rocket.Chat
  attempt specifically exercises the new extra-config check path. Zero
  unexpected console errors (only the two expected 503s). Frontend rebuilt
  afterward without the sandbox-only backend URL override.
- Explicitly out of scope (see board): WhatsApp Business, Viber, Google
  Calendar push/renewal, reply for issue/PR-comment-shaped or
  meeting-shaped sources, Generic HTTP Connector edit (PATCH).

2026-07-02 — Sprint 16 opened and closed (S16-01): Generic HTTP Connector edit (PATCH) + a real CORS bug found and fixed:

- New planning board: `docs/planning/SPRINT16_TASK_BOARD.md`. Continuing
  under the user's "continue where you can, on your own" delegation.
  Closes the "editing an existing Generic HTTP Connector config" gap
  flagged as a follow-up in both the Sprint 13 and Sprint 15 boards — pure
  CRUD completion on a feature that already existed end-to-end (Sprint 10
  backend, Sprint 13 UI), no new infra or integration.
- Backend: new `PATCH /api/v1/ingestion/connectors/generic/{config_id}` in
  `backend/app/api/generic_connectors.py`. `name`/`slug` deliberately
  immutable — `slug` drives `source_type` (`generic:{slug}`), already
  referenced by historical `connector_runs`/`connectors` telemetry and the
  webhook secret env-var name (`ALLINO_GENERIC_{SLUG}_WEBHOOK_SECRET`);
  changing it post-creation would orphan history and silently break a
  configured webhook secret. Editable: `base_url`, `auth_method`,
  `auth_header_name`, `poll_interval_seconds`, `field_mapping`,
  `webhook_enabled`. Uses `exclude_unset=True` for a true partial update;
  the `auth_header_name`-required-for-`api_key` check runs against the
  *merged* resulting state, not just the fields in the PATCH body.
- New repo function `update_generic_connector(...)` in
  `backend/app/db/repositories/generic_connectors_repo.py` — dynamic `SET`
  clause built from a fixed field whitelist (no injection surface),
  `updated_at = CURRENT_TIMESTAMP` set explicitly (SQLite's column
  `DEFAULT CURRENT_TIMESTAMP` only fires on INSERT, same pattern already
  used in `connectors_repo.py`).
- Frontend: `frontend/src/lib/api.ts` adds `updateGenericConnector(...)`.
  `frontend/src/components/GenericConnectorsPanel.tsx` adds an "Edit"
  button per row that opens the existing create-form UI pre-filled
  (`Name` shown disabled — immutable) and submits a PATCH instead of a
  POST; "Cancel" discards the in-progress edit without persisting anything.
- **Found and fixed a real pre-existing CORS bug while doing the mandatory
  live-browser verification (not originally in scope — same "verify live,
  not just build" pattern as the Sprint 7 CSP catch and Sprint 11 hydration
  catch):** `backend/app/main.py`'s `CORSMiddleware` had
  `allow_methods=["GET", "POST", "DELETE"]` — `PATCH` was never added
  because no endpoint used it before this sprint. The browser's CORS
  preflight failed silently from `pytest`'s/`tsc`'s perspective (a
  `TestClient`-based test doesn't run real browser preflight checks) — only
  visible as a real browser console error, exactly the class of bug this
  mandatory-live-verification rule exists to catch. Fixed: added `"PATCH"`
  to `allow_methods`. Added `backend/tests/test_cors_methods.py` as a
  permanent regression test asserting an `OPTIONS` preflight for the PATCH
  route returns `PATCH` in `Access-Control-Allow-Methods` — this exact
  failure mode (add a write endpoint, forget the CORS method list) can now
  be caught by `pytest` too, not just by re-discovering it live again.
- Tests: `backend/tests/test_generic_connectors_repo.py` (new — repo-level
  partial update, unknown-field ignored, nonexistent-id/wrong-tenant return
  `None`), `backend/tests/test_generic_connector_endpoints.py` extended
  (PATCH: partial update, 404 unknown id, 422 api_key-without-header,
  tenant isolation), `backend/tests/test_cors_methods.py` (new, see above).
- Verified: backend `pytest -q` => 233 passed (up from 222);
  `ruff check app tests --select F,E9` => all checks passed. Frontend:
  `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification: created a test connector, edited it (first
  attempt hit the CORS bug above, fixed, retried — succeeded), confirmed
  the `api_key`-without-header validation still blocks save on update the
  same way it does on create, confirmed Cancel discards an unsaved edit,
  cleaned up via Delete. Zero unexpected console errors after the fix.
  Frontend rebuilt afterward without the sandbox-only backend URL override.

2026-07-02 — Sprint 17 opened and closed (S17-01/S17-02): reply extended to GitHub, GitLab, Jira, Linear:

- New planning board: `docs/planning/SPRINT17_TASK_BOARD.md`. User
  explicitly asked (via plain-language `AskUserQuestion` exchange) to
  extend reply/write-back to these four issue-tracker sources — for these,
  "reply" means posting a comment on the issue/PR/ticket, not a chat
  message, confirmed with the user before implementation.
- **Technical finding surfaced to the user first:** Jira and Linear are
  self-sufficient — their `external_id` already is exactly what each
  provider's comment API needs. GitHub and GitLab are not: `external_id`
  is the *notification* id, not the issue/PR itself; the real address only
  existed in ingestion-time `payload` (`subject_url`/`target_url`), which
  `messages` never persisted (only `preview`/`thread_key`/`priority`
  survive normalization, by design since Sprint 11). User chose: add a
  column rather than skip GitHub/GitLab.
- New migration `backend/migrations/0012_reply_target.sql`:
  `ALTER TABLE messages ADD COLUMN reply_target TEXT` (nullable, additive).
  `backend/app/domain/events.py`: `InboxMessage.reply_target: str | None`.
  `backend/app/services/normalizer.py`: populated from
  `payload["subject_url"]` (GitHub) / `payload["target_url"]` (GitLab),
  `None` otherwise. `backend/app/db/repositories/messages_repo.py`:
  encrypted at rest via the existing `encrypt_text`/`decrypt_text` helpers,
  same treatment as `preview` (`CLAUDE.md` §4 field-level encryption
  policy).
- New reply senders: `send_github_reply()` (`POST {reply_target}/comments`,
  `Bearer` token), `send_gitlab_reply()` (parses the web URL in
  `reply_target` into project-path/noteable-type/iid, `POST .../notes`,
  `PRIVATE-TOKEN` header), `send_jira_reply()` (`POST
  .../issue/{external_id}/comment`, Atlassian Document Format body,
  `external_id` alone is sufficient), `send_linear_reply()` (GraphQL
  `commentCreate` mutation, `external_id` alone is sufficient).
- `backend/app/api/replies.py`: all 4 wired into `_REPLY_TOKEN_ENV_KEYS`/
  `_REPLY_SENDERS`; new `_REQUIRES_REPLY_TARGET = {"github", "gitlab"}`
  check — a message with no recorded `reply_target` (ingested before this
  migration, or a notification whose subject wasn't a commentable
  issue/PR) is rejected with `400`, not treated as a `503` config problem.
  `frontend/src/lib/types.ts`: `REPLY_SUPPORTED_SOURCES` now includes all 4.
- Tests: `backend/tests/test_reply_delivery.py` extended with all 4 new
  senders (request shape, missing-target/missing-id `ValueError`,
  API-error `RuntimeError`, GitLab URL-parsing edge cases including
  merge-request URLs with a `#note_xxx` fragment).
  `backend/tests/test_reply_endpoint.py` extended: GitHub/GitLab success +
  missing-`reply_target` `400`, Jira/Linear success (no `reply_target`
  needed); also fixed a now-stale test (`test_reply_to_unsupported_source_returns_400`
  used `sourceType: "github"`, which broke once GitHub became a supported
  reply source — switched to `zoom`, which remains genuinely unsupported).
- Verified: backend `pytest -q` => 252 passed (up from 233); `ruff check
  app tests --select F,E9` => all checks passed. Frontend `tsc --noEmit`
  clean; `npm run build` => success.
- Live browser verification (real backend + real frontend, sandboxed
  browser tool via `host.docker.internal:8000`): seeded one item per new
  source, confirmed the composer now renders for all four (was "not
  supported"), and that sending with no provider token configured
  correctly surfaces the fail-closed 503 for all four — exercising the
  full `reply_target` round-trip (ingest → encrypted column → decrypt →
  reach the config check) end to end. Zero unexpected console errors.
  Frontend rebuilt afterward without the sandbox-only backend URL
  override.
- Explicitly out of scope (see board): WhatsApp Business, Viber, Google
  Calendar push/renewal, reply for Zoom/Teams (meeting-shaped, no reply
  semantics), backfilling `reply_target` for GitHub/GitLab messages
  ingested before this migration (those rows simply can't be replied to
  until re-ingested — the discarded payload can't be recovered).

2026-07-02 — Architectural fork decisions recorded (no code changed):

- Asked the user in plain language via `AskUserQuestion` about two open
  forks left from Sprint 17 (Google Calendar push, WhatsApp/Viber webhook
  connectors). Both times the user picked the conservative/recommended
  option — deliberate decision, not deferral by default.
- **Google Calendar push/watch-channel renewal:** stays REST-polling only.
  Building push would require a new scheduler-infrastructure component
  (to renew Google's watch-channel subscription roughly weekly) that no
  connector in this project has yet. Re-open only if the user explicitly
  asks for near-real-time Calendar updates and is willing to fund building
  that scheduler component.
- **WhatsApp Business / Viber:** both deferred, not started. Both are
  webhook-push-only APIs (no poll/list endpoint), so either requires a new
  "webhook-receiver connector" architecture shape not yet built for any
  in-project source, *plus* real external setup (Meta business
  verification for WhatsApp, Viber public-account registration) the user
  would need to complete outside the codebase before either could actually
  connect to a live account. Re-open only on explicit user request to
  build this new connector shape.

2026-07-02 — Sprint 18 opened and closed: scheduler worker built

- New planning board: `docs/planning/SPRINT18_TASK_BOARD.md`. Follow-up to the
  same-day architectural-fork discussion above: user asked for an effort
  estimate on the scheduler component described there, then explicitly asked
  for it to be built.
- **Scope kept minimal:** only makes `poll_interval_seconds` on Generic HTTP
  Connectors actually work (dead config field since Sprint 10). Did NOT build
  Google Calendar watch-channel renewal or a generic `scheduled_jobs` table —
  those stay deferred; see the board for the reasoning (no second job type
  exists yet to justify a generic jobs table).
- New `backend/app/services/connector_sync.py` — shared fetch+ingest logic,
  used by both the manual `/sync` endpoint and the new worker (no duplicated
  code paths).
- New `backend/app/workers/scheduler_worker.py` — same shape as
  `event_bus_worker.py` (`--healthcheck` flag, `main()`/loop), polls DB
  instead of Redis. Due-ness computed from existing
  `connectors.last_synced_at`, no new migration.
- New `docker-compose.yml` service `scheduler_worker`.
- Tests: `backend/tests/test_scheduler_worker.py` (new, 8 tests).
- Verified: `pytest -q` => 260 passed (up from 252); `ruff check app tests
  --select F,E9` clean. **Live real-process verification:** real backend +
  real registered connector + real mock HTTP source + the worker run as an
  actual separate process (`--once`), not mocked — confirmed it fetches on
  its own, respects the interval on immediate re-run, and correctly fires
  again once the interval elapses. No frontend touched, so no browser
  verification step applies this sprint.

2026-07-02 — Live UI check after Sprint 18; one known bug found, not fixed

- User ran a full local check (backend + frontend, both started fresh) and
  spotted a visual bug in Settings: the "+ Add connector" button in
  `frontend/src/components/GenericConnectorsPanel.tsx:234` uses the
  `.icon-btn` CSS class (`frontend/src/app/globals.css:241`), which is a
  fixed 32×32px box meant for a single icon glyph. A multi-word text label
  doesn't fit and overflows/clips. Not a type or build error — `tsc`/`next
  build` are both clean, this is pure CSS sizing.
  **Not fixed — pick up next session.** Options: give the button its own
  padding-based (non-fixed-width) class, or switch to an icon-only "+" with
  a tooltip/aria-label instead of a text label.
- No other issues found in this pass: inbox loaded 56 messages across all
  10 sources, connector status/recent-runs panel populated correctly,
  thread view (security banner, message, reply composer) opened and
  rendered correctly.
- All dev processes (backend uvicorn, frontend, and the scratch mock-server
  + scratch backend used for the Sprint 18 live-process check) were stopped
  at end of session; `frontend/.env.local` confirmed back to
  `http://localhost:8000` (the `host.docker.internal` override used only
  for the sandboxed-browser check was reverted, per the standing rule in
  this file's browser-verification notes).

2026-07-03 — Sprint 19 opened and closed: Google Calendar auto-polling via the scheduler worker:

- New planning board: `docs/planning/SPRINT19_TASK_BOARD.md`. User asked whether
  Google Calendar could already be auto-synced now that the Sprint 18 scheduler
  worker exists. Correct instinct, wrong premise: the worker was hardcoded to
  `list_generic_connectors_with_polling()` (Generic HTTP Connectors only) —
  built-in connectors like Google Calendar have no persisted per-tenant config
  row to poll from. Asked the user two plain-language questions before building:
  (1) real Google Push API vs simple periodic polling — user picked polling;
  (2) env-scoped single-tenant config vs a new persisted per-tenant config table
  — user picked env-scoped (matches the existing single-token-per-deployment
  model already used for `ALLINO_GOOGLE_CALENDAR_TOKEN`).
- New env vars in `core/config.py`: `ALLINO_GOOGLE_CALENDAR_POLL_ENABLED`,
  `_INTERVAL_SECONDS` (default 900), `_TENANT_ID`, `_CALENDAR_ID` (default
  `primary`). Scoped to exactly one tenant/calendar per deployment — not a
  DB-driven list.
- `backend/app/services/connector_sync.py` adds `sync_google_calendar_connector()`
  + `GoogleCalendarSyncError`, mirroring `sync_generic_connector()` exactly —
  reuses the same shared `record_batch_result()` as the manual sync endpoint, no
  duplicated ingest/telemetry/audit logic.
- `backend/app/workers/scheduler_worker.py`: new `_is_google_calendar_due()`
  (same due-check shape as `_is_due()`, keyed off the env-configured tenant) and
  `run_scheduler_tick()` extended to check + sync it after the generic-connector
  loop.
- `docker-compose.yml` (`scheduler_worker` service) and `backend/.env.example`
  updated with the new vars; `ALLINO_SCHEDULER_WORKER_POLL_INTERVAL_SECONDS`
  (existed since Sprint 18) documented in `.env.example` for the first time.
- Tests: `backend/tests/test_scheduler_worker.py` extended with 7 new tests
  (due-check: disabled / no tenant / never synced / recent / stale; tick:
  syncs when due, records failure without raising).
- Verified: `pytest -q` => 267 passed (up from 260); `ruff check app tests
  --select F,E9` => clean. **Live real-process verification** (not just mocked
  unit tests): ran `python -m app.workers.scheduler_worker --once` as a real
  separate process against a scratch DB (no Google token, so 0 events fetched
  — exercises the wiring, not the Google API itself). First tick synced
  (never-synced-before), `connectors` table got `tenant_demo:google_calendar`
  row with `status=healthy`; second tick immediately after correctly synced 0
  (interval not elapsed). Scratch DB removed after. No frontend touched, so no
  browser verification step applies.
- Explicitly out of scope (see board): real Google Push API / watch-channel
  renewal (separate architecture decision, stays deferred — unchanged from
  Sprint 17/18); polling more than one tenant's calendar (would need the
  persisted-config-table path, not chosen); auto-polling any other built-in
  connector (Zoom/Teams/Slack/etc.) — only Google Calendar was in scope this
  sprint.

2026-07-03 — Sprint 20 opened and closed: fixed the `.icon-btn` text-overflow bug (Settings + Security Center):

- New planning board: `docs/planning/SPRINT20_TASK_BOARD.md`. User delegated
  ("choose what to do next yourself and do it") — picked the known unfixed
  bug flagged at the end of the 2026-07-02 live UI check: the "+ Add
  connector" button in `GenericConnectorsPanel.tsx` used `.icon-btn` (fixed
  32×32px, meant for a single icon glyph), clipping its text label.
- Grepped every `.icon-btn` usage across the frontend to check for the same
  defect class, not just the one flagged instance — found **three**, not one:
  `GenericConnectorsPanel.tsx:223` ("+ Add connector"/"Cancel"),
  `GenericConnectorsPanel.tsx:410` ("Retry", error state, not previously
  flagged), `SecurityCenter.tsx:125` ("Retry", audit-log error state).
- Fixed all three by replacing `className="icon-btn"` with the exact
  padding-based inline button style already used for the "Edit"/"Delete" row
  buttons in the same file — reused an existing in-file pattern instead of a
  new CSS class. `.icon-btn` itself untouched; its 3 remaining callers
  (Search/Archive/Snooze) are genuine single-icon buttons and still correct.
- Verified: `tsc --noEmit` clean; `npm run build` success. **Live browser
  verification** using `browser_snapshot(boxes: true)` for exact pixel
  measurement (more precise than eyeballing a screenshot for a sizing bug):
  all 3 fixed buttons now render at their natural content width (117px /
  58px / 51px / 54px depending on label) instead of clipped at 32px.
  Simulated fetch failures (patched `window.fetch` via `browser_evaluate`,
  not a real backend outage) to reach both Retry error states, confirmed
  Retry actually recovers data after unpatching fetch, zero unexpected
  console errors. Verification processes stopped via `taskkill //PID ... //F`
  (netstat-confirmed clean); `frontend/.env.local` reverted to
  `http://localhost:8000` and rebuilt before ending the session.
- No backend changes — pure frontend fix, backend suite unchanged (267
  passed).

2026-07-03 — Sprint 21 opened and closed: onboarding screen (connect-a-source gate, skippable):

- New planning board: `docs/planning/SPRINT21_TASK_BOARD.md`. User delegated
  again ("continue on your own") with no specific task. Ran a research agent
  to cross-reference `PROJECT_MASTER_BRIEF.md`/`PREBUILD_SPEC_V1.md` against
  what's actually implemented, ruling out everything already explicitly
  deferred. Onboarding surfaced as the strongest candidate: both docs
  require it ("must require connecting at least one source, but not block
  the user forever on Skip"), and grep confirmed zero onboarding component
  ever existed. Two other candidates found (decorative Snooze/Archive
  buttons with no `onClick`; decorative Search icon with no backend FTS)
  were explicitly set aside as bigger/separate units of work, not silently
  dropped — see the Sprint 21 board. MFA-for-admin-paths (a real open P0
  Security Gate line) was flagged as needing a real user decision rather
  than picked up autonomously, since building it now would mean inventing
  an admin surface just to gate it.
- New `frontend/src/components/OnboardingScreen.tsx`: shown when the inbox
  is empty, no built-in source is configured, and the user hasn't skipped it
  before (persisted in `localStorage`, survives across sessions — Skip never
  blocks forever). Both action buttons route to the existing Settings flow
  rather than duplicating connector-creation logic.
- `frontend/src/app/page.tsx`: new `onboardingSkipped` state restored from
  `localStorage` in a mount-only effect (SSR-safe default, same
  hydration-mismatch-avoidance pattern as the existing mode/filters
  `sessionStorage` restoration from Sprint 11); `showOnboarding` gates on
  mode, skip state, capabilities-loaded, empty inbox, and no configured
  capability.
- **Deliberate simplification, stated explicitly:** does not separately
  check for a registered-but-unsynced Generic HTTP Connector — would need
  its own one-off fetch just to inform a dismissal heuristic. Acceptable:
  Skip or an arriving message both resolve it.
- Verified: `tsc --noEmit` clean; `npm run build` success. **Live browser
  verification**, explicitly re-checking the Sprint 11 hydration-mismatch
  bug class for the new `localStorage` read: reloaded with the skip flag
  already persisted — zero console errors, stayed correctly hidden. Also
  verified onboarding reappears on repeat empty visits (not a one-shot
  fluke), both action buttons switch to Settings, Skip hides it, and seeding
  5 real messages via `/seed` suppresses onboarding independent of the skip
  flag. Zero console errors across every step. Verification processes
  cleaned up, `.env.local` reverted, scratch DB removed.
- No backend changes — pure frontend feature on existing endpoints, backend
  suite unchanged (267 passed).

2026-07-03 — Sprint 22 opened and closed: wired Archive/Snooze (were decorative dead buttons):

- New planning board: `docs/planning/SPRINT22_TASK_BOARD.md`. User delegated
  again ("продолжай"). Sprint 21's board had already flagged this as the
  next-best candidate: `ThreadPanel.tsx:432-440`'s Archive/Snooze icon
  buttons had no `onClick` at all. Picked over the other two Sprint 21
  candidates (Search needs new backend FTS; MFA-for-admin-paths needs a real
  user decision) as the smallest, most self-contained unit — mirrors the
  existing reply permission-tier/per-message-endpoint shape almost exactly.
- New migration `0013_message_state.sql`: additive `messages.archived_at` /
  `messages.snoozed_until` (nullable). `messages_repo.list_messages` now
  filters both out of `/inbox`/`/inbox/page` by default; existing rows/tests
  unaffected since both columns are NULL for everything ingested before this
  migration. New `archive_message()`/`snooze_message()` repo functions.
- New JWT permission tier (mirrors sync/read/reply exactly):
  `ALLINO_JWT_MESSAGE_ACTIONS_ROLES`/`_SCOPES` in `core/config.py`,
  `require_message_actions_permission` in `core/security.py`.
- New router `backend/app/api/message_actions.py`: `POST
  /messages/{event_id}/archive` and `.../snooze` (optional `{"hours": n}`
  body, default 4h, `0 < hours <= 720`). Both `404` on unknown/wrong-tenant,
  audit-logged on success (`message.archived`/`message.snoozed`).
- Frontend: `lib/api.ts` adds `archiveMessage()`/`snoozeMessage()`
  (mirrors `sendReply()`). `ThreadPanel.tsx`'s two previously-dead icon
  buttons now call these with local pending/error state (same pattern as
  the existing `ReplyComposer`); `page.tsx` gets one `handleMessageRemoved`
  callback that drops the item from local state and clears selection on
  success (instant UX instead of waiting for the next ~20s poll).
- **Deliberate simplifications, stated explicitly, not silently cut:** no
  "view archived"/unarchive UI (archive is currently one-directional from
  the UI); no snooze-duration picker (fixed 4h default; the endpoint already
  accepts an `hours` override for future UI use); `count_messages` (used by
  `/stats`) intentionally left as a total-ingested metric, not changed to
  reflect inbox visibility.
- Verified: backend `pytest -q` => 277 passed (up from 267, new
  `test_message_actions.py` — 10 tests including tenant isolation, JWT
  permission tier, and an expiry test that sets a past `snoozed_until`
  directly via the repo layer rather than manipulating wall-clock time);
  `ruff check app tests --select F,E9` clean. Frontend `tsc --noEmit` clean;
  `npm run build` success. **Live browser verification**: seeded 5 messages,
  archived one (inbox 5→4, message vanished, thread reset, zero console
  errors), snoozed another (4→3, same), cross-checked directly against the
  backend afterward (`/inbox` returned exactly the 3 remaining ids, `/audit`
  had both action entries). Verification processes cleaned up, `.env.local`
  reverted, scratch DB removed.
- Explicitly still open (see board): "view archived" filter, snooze duration
  picker, the Sprint 21 Search/MFA candidates — unchanged by this sprint.

2026-07-03 — Sprint 23 opened and closed: Snooze duration picker (frontend-only):

- New planning board: `docs/planning/SPRINT23_TASK_BOARD.md`. User delegated
  again ("продолжай"). Sprint 22's board listed this as one of two immediate
  follow-ups; picked over "view archived"/unarchive because it needed zero
  backend work — `POST .../snooze` already accepted an `{"hours": n}`
  override since Sprint 22, added for exactly this future use.
- `ThreadPanel.tsx`'s Snooze button now opens a small `role="menu"` dropdown
  (4 fixed options: 1 hour / 4 hours / Tomorrow 9 AM / Next week) instead of
  immediately snoozing for a hardcoded 4h; picking an option calls the
  existing endpoint with that duration. Closes on pick, on a full-viewport
  backdrop click, or when the open thread changes. `lib/api.ts`'s
  `snoozeMessage()` gained an optional `hours` param. New
  `.menu-item:hover`/`:focus-visible` CSS rules in `globals.css` (inline
  styles can't express `:hover`, same reason `.icon-btn` is a class).
  Deliberately 4 fixed options, not a free-form datetime picker — separate
  bigger component if ever needed.
- Verified: no backend changes (re-ran the suite anyway: 277 passed,
  unchanged). Frontend `tsc --noEmit` clean; `npm run build` success. **Live
  browser verification**: opened the menu (4 options positioned correctly),
  picked "Tomorrow, 9 AM" — inbox 5→4, message vanished, audit log's
  `snoozed_until` confirmed as the actual computed next-day-9AM timestamp
  (not a placeholder). Opened the menu again and clicked outside it —
  confirmed it closes **without** snoozing (inbox count unchanged, no new
  audit entry); Playwright's own strict-actionability refusal to click
  through the backdrop on a normal click incidentally confirmed the
  backdrop really does intercept pointer events as designed. Verification
  processes cleaned up, `.env.local` reverted, scratch DB removed.
- Explicitly still open: "view archived"/unarchive UI, the Sprint 21
  Search/MFA candidates — unchanged by this sprint.

2026-07-03 — Sprint 24 opened and closed: "View archived" + Unarchive:

- New planning board: `docs/planning/SPRINT24_TASK_BOARD.md`. User delegated
  again ("окей, продолжай"). Last small candidate from the Sprint 22 board:
  archiving was one-directional — no UI (or even a query option) to see or
  recover an archived message. Picked over Search/MFA (still open from
  Sprint 21) since it needed no new architecture decision.
- `messages_repo.list_messages()`/`list_messages_page()` gain
  `archived_only: bool = False` — a *separate* view (archived_at IS NOT
  NULL), not merged into the active list. New `unarchive_message()`.
  `/inbox` and `/inbox/page` gain an `archived` query flag. New `POST
  /messages/{event_id}/unarchive` (same shape as `archive`/`snooze`, same
  permission tier, no new one needed).
- Frontend: `lib/api.ts` adds `fetchArchivedMessages()`/`unarchiveMessage()`.
  New `components/ArchivedList.tsx` — self-fetching, own
  loading/error/empty states, one "Unarchive" button per row. Deliberately
  a separate component from `InboxList.tsx` (archived rows aren't
  thread-selectable). `page.tsx` gets a `showArchived` toggle — an icon
  button next to Search in the Inbox header (using the already-existing,
  previously-unused `ArchiveIcon`) swaps the message-list column's content;
  **not a 6th L1 nav section** (`CLAUDE.md` §6 fixes the shell to 5).
- **Deliberate simplification, verified working, not just assumed:** no
  optimistic re-insertion into the live inbox list on unarchive — the
  message reappears via the existing ~20s background poll, same freshness
  model as connector status elsewhere in this app. Confirmed live: after
  unarchiving and returning to Inbox, the count had already self-corrected
  to 5 by the time of the check.
- Verified: backend `pytest -q` => 280 passed (up from 277); `ruff` clean.
  3 new tests in `test_message_actions.py` (archived view membership,
  unknown-message unarchive 404, unarchive restores + audits) plus a
  tenant-isolation assertion added to the existing cross-tenant test.
  Frontend `tsc --noEmit` clean; `npm run build` success. **Live browser
  verification** (zero permission prompts this time — see the
  `mcp__MCP_DOCKER__browser_*` allowlist note below): archived a message,
  opened the archived view (item shown with Unarchive, thread panel
  undisturbed), unarchived it (empty state shown correctly), returned to
  Inbox (count self-corrected via poll), cross-checked directly against the
  backend (`/inbox`=5, `/inbox?archived=true`=0, both audit actions
  present). Zero console errors throughout. Verification processes cleaned
  up, `.env.local` reverted, scratch DB removed.
- Also this session (not a sprint, a standing config change): user asked to
  stop being prompted for MCP Docker browser-automation tools in this
  project. Added all `mcp__MCP_DOCKER__browser_*` tool names (navigate,
  click, snapshot, evaluate, console_messages, take_screenshot, etc.) to
  `.claude/settings.local.json`'s permission allowlist — deliberately
  excluding `browser_run_code_unsafe` and the `mcp-exec`/`mcp-add`/
  `mcp-remove`/`mcp-config-set`/etc. MCP-server-management tools (asked the
  user first; they chose the narrower browser-only scope). This file is
  local/gitignored, not committed — a personal convenience on this machine,
  not a team policy.
- Explicitly still open: the Sprint 21 Search/MFA candidates.

2026-07-03 — Sprint 25 opened and closed: Inbox search (exact match):

- New planning board: `docs/planning/SPRINT25_TASK_BOARD.md`. User was asked
  to choose exact vs fuzzy search (Sprint 21's decorative-Search-icon gap);
  picked exact match, described as a proper/full search, not a stub.
- **Security tradeoff surfaced and resolved conservatively, not asked
  about**: `messages.preview` is encrypted at rest. A conventional FTS5
  index needs plaintext tokens — building one would mean persisting a
  second, searchable plaintext copy of message content, a real regression
  of that guarantee. The user asked for exact-match search, not "weaken
  encryption at rest," so the conservative reading was applied without
  needing a separate question: `search_messages()` decrypts a bounded,
  recency-ordered window of active messages (`_SEARCH_SCAN_LIMIT = 5000`,
  documented) through the same `_map_rows()` path every other read uses,
  and matches in Python (case-insensitive substring over preview/
  external_id/source) — zero new persisted plaintext anywhere. Documented
  scale limit, not hidden: if a tenant's active volume ever exceeds the
  scan window, that's the trigger to have the FTS-vs-encryption
  conversation explicitly, not default into it.
- `backend/app/db/repositories/messages_repo.py` adds `search_messages()`.
  New `GET /api/v1/ingestion/search?q=...` in `ingestion.py`, reusing
  `require_ingestion_read_permission` (same tier as `/inbox`, no new
  permission surface). Search covers active messages only (same default as
  `/inbox` — archived/snoozed excluded, deliberate scope cut).
- Frontend: `lib/api.ts` adds `searchMessages()`. New
  `components/SearchPanel.tsx` — self-contained, debounced (300ms),
  loading/empty/no-results/error states, reuses the existing `InboxList`
  to render results (selecting one behaves exactly like a normal inbox
  click — opens the thread with reply/archive/snooze all live). `page.tsx`
  wires the previously-decorative Search icon button to a `searchOpen`
  toggle, same content-swap pattern as the Sprint 24 Archived toggle.
- Verified: backend `pytest -q` => 288 passed (up from 280, new
  `test_search.py` — 8 tests: preview match, external_id match, case-
  insensitivity, no-match empty list, archived exclusion, tenant isolation,
  limit respected, empty query rejected). `ruff` clean. Frontend `tsc
  --noEmit` clean; `npm run build` success. **Live browser verification**
  (zero permission prompts): seeded two messages with deliberately distinct
  text, searched "migration" — only the matching one appeared (confirmed
  the non-match was actually excluded); clicked it — search closed, correct
  thread opened, fully functional (not a dead-end). Searched a guaranteed
  no-match string — correct empty state, not an error. Zero console errors.
  Verification processes cleaned up, `.env.local` reverted, scratch DB
  removed.
- Explicitly still open: MFA for admin paths — discussed with the user
  (concrete example given), but they haven't decided whether this project
  needs an admin panel at all yet; no board opened.

2026-07-03 — Sprint 26 opened and closed: Admin MFA (TOTP step-up) + first admin action (delete all tenant messages):

- New planning board: `docs/planning/SPRINT26_TASK_BOARD.md`. `CLAUDE.md` §4
  "MFA for admin paths" has been open since the project started — no admin
  surface ever existed to gate. User was asked directly, twice, in plain
  language before any code was written (what to build, then which of two
  MFA depths); chose a lightweight TOTP step-up on *existing* auth (not new
  user accounts/login/sessions — this service has never issued its own
  tokens, only verified externally-issued ones), and "delete all tenant
  messages" as the first action to protect. Full architecture research via
  an Explore agent, then a written/approved plan (`EnterPlanMode`/
  `ExitPlanMode`) before touching any file — this sprint had too many real
  forks to improvise, unlike most sprints this session.
- **Key structural decision**: unlike the other 4 permission tiers (which
  treat the API key as fully trusted and skip role checks),
  `require_admin_mfa_permission` in `core/security.py` does NOT skip the
  TOTP check for API-key callers — the whole point of a second factor is
  that it applies regardless of the first factor. Verified by a dedicated
  test.
- New `ALLINO_JWT_ADMIN_ROLES`/`_SCOPES` (admin-only by default, narrower
  than other tiers) + `ALLINO_ADMIN_TOTP_SECRET` (env/Vault-only, resolved
  fresh per-request like every other secret — no QR-enrollment UI, `pyotp`
  added as a dependency). New `messages_repo.delete_all_messages()` (hard
  delete, any state, `messages` table only — scoped explicitly, not a full
  tenant wipe). New router `backend/app/api/admin.py`:
  `POST /api/v1/admin/tenant/messages/delete` (body must confirm the exact
  tenant id, `400` if not; success is audit-logged). `/api/v1/admin`
  literally becomes "the admin path" — home for future admin actions.
  `/api/v1/admin` added to the rate-limited path predicate.
- Frontend: new `components/DangerZone.tsx` (confirm-text + TOTP-code
  form) rendered at the bottom of `SettingsPanel.tsx` — **not a 6th L1 nav
  section**, respects the `CLAUDE.md` §6 fixed 5-section shell.
- **Real CORS bug found and fixed during mandatory live verification** —
  same class as the Sprint 16 PATCH lesson, but for a header: `X-TOTP-Code`
  wasn't in `CORSMiddleware.allow_headers` (an explicit whitelist).
  Invisible to `pytest` (`TestClient` doesn't run real preflight); only
  surfaced as a real browser CORS console error. Fixed; added a permanent
  regression test in `test_cors_methods.py` mirroring the existing PATCH
  one.
- **Test-suite fragility found and fixed** (root cause pre-existing, not
  introduced by this feature): `rate_limit.py`'s `RATE_LIMITER` is a
  module-level singleton, a real wall-clock window, never reset between
  test files. The new admin test file's request volume pushed it over
  threshold for unrelated later files (`test_message_actions.py`,
  `test_metrics.py`), causing order-dependent flakiness. Fixed at the
  root in `tests/conftest.py`'s `pytest_runtest_setup` (which already
  resets other global security state before every test): now also calls
  `rate_limit.RATE_LIMITER.clear()` — prevents any future test file from
  tripping this again, not just a one-file workaround.
- Verified: backend `pytest -q` => 298 passed (up from 288: 9 new
  `test_admin_actions.py` + 1 new CORS regression test); `ruff` clean.
  Frontend `tsc --noEmit` clean; `npm run build` success. **Live browser
  verification**: generated a real TOTP secret, seeded 5 messages, Danger
  Zone delete button correctly stayed disabled until the tenant id was
  typed exactly; a deliberately wrong TOTP code correctly showed "Invalid
  TOTP code" and left all 5 messages untouched (confirmed against the
  backend); a real generated code succeeded ("Deleted 5 messages."),
  cross-checked directly against the backend (`/inbox`=0,
  `/inbox?archived=true`=0, audit log has
  `admin.tenant_messages.deleted` with `deleted_count: 5`). Verification
  processes cleaned up, `.env.local` reverted, scratch DB removed.
- Explicitly out of scope (see board): other admin actions (export audit
  log, rotate API key, etc.) — the MFA plumbing is generic, adding a
  second action is now a small same-pattern extension; deleting
  `outbound_replies`/`connectors`/audit trail (only `messages` touched);
  TOTP enrollment UI; the pre-existing "frontend never sends X-API-Key"
  gap (inherited as-is).

2026-07-03 — Sprint 27 opened and closed: second admin action, export tenant audit log:

- New planning board: `docs/planning/SPRINT27_TASK_BOARD.md`. Opened under
  the user's usual open-ended "продолжай" delegation; Sprint 26 had
  explicitly named "export audit log" as the next same-pattern admin
  action (reuses `require_admin_mfa_permission`, no new architecture), so
  it was picked without needing to ask — unlike "rotate API key" (touches
  a live secret, real design questions about what "rotate" even means when
  the key lives in env/Vault) which stays deferred.
- `backend/app/api/admin.py`: `GET /api/v1/admin/tenant/audit/export`,
  gated by the same `require_admin_mfa_permission` dependency as the
  delete action (TOTP required unconditionally, even for a trusted API
  key). Reuses the existing `list_audit(tenant_id, limit)` repository
  function directly with a fixed `limit=10000` cap — no new repository
  function needed (same "check whether the existing path is already
  sufficient" lesson from Sprint 17). Self-audits like the delete action
  (`admin.tenant_audit.exported`, `{"exported_count": n}`).
- Frontend: `lib/api.ts` adds `exportTenantAudit(totpCode)` — fetches the
  export and triggers a client-side file download (Blob + object URL), no
  backend `Content-Disposition` needed. New
  `components/AdminAuditExport.tsx` — a plain (non-"danger"-styled) admin
  tools box since this action is non-destructive; mounted in
  `SettingsPanel.tsx` above `DangerZone` (destructive vs. non-destructive
  admin actions visually separated). Still not a 6th L1 nav section.
- No new CORS changes needed: `GET` and `X-TOTP-Code` were already
  whitelisted by the Sprint 16 and Sprint 26 fixes respectively — confirmed
  live, not just assumed.
- Verified: backend `pytest -q` => 304 passed (up from 298: 6 new tests).
  `ruff` clean. Frontend `tsc --noEmit` clean; `npm run build` success.
  **Live browser verification**: wrong TOTP code showed "Invalid TOTP
  code" inline (console showed only the expected `403`, no CORS error);
  real TOTP code triggered a real file download and "Exported 1 audit
  entry.", cross-checked directly against the backend (`admin.tenant_audit
  .exported` audit entry present with matching `exported_count`). Zero
  unexpected console errors. Verification processes cleaned up, `.env.local`
  reverted, scratch DB removed.
- Explicitly still out of scope: rotate API key / manage JWT role config
  (each a real config-mutation decision, not a drop-in extension); a
  backend `Content-Disposition` header (frontend triggers the download
  client-side instead); export limit above 10000 rows or a streaming/
  paginated export (documented cap, not hidden — same reasoning as the
  Sprint 25 search scan-limit).

2026-07-03 — Sprint 28 opened and closed: third admin action, rotate API key (candidate generator, not live):

- New planning board: `docs/planning/SPRINT28_TASK_BOARD.md`. User asked
  directly what "rotate API key" and "manage JWT role config" meant (plain-
  language explanation given first, no jargon), then asked to proceed with
  API-key rotation.
- **Key research finding that shaped scope**: `ALLINO_API_KEY` is read from
  env-or-Vault once at process import time (a module-level constant in
  `core/config.py`), not per-request like the admin TOTP secret is. A truly
  *live* rotation (old key dead / new key live, no restart) is only
  possible if the key lives in Vault, and even then `core/secrets.py` only
  supports reading from Vault today, not writing — plus Vault isn't
  actually deployed in this project's `docker-compose.yml`
  (`ALLINO_VAULT_ENABLED` defaults false, no Vault service exists). This
  was surfaced to the user via `AskUserQuestion` as two real options: (1)
  stand up Vault + add a Vault-write path for true live rotation (bigger,
  separate infrastructure work), or (2) a candidate-key generator with no
  live effect — admin copies the value into `.env`/Vault and restarts
  manually, same as today's process minus hand-generating a random string.
  User picked option 2 (marked recommended).
- `backend/app/api/admin.py`: `POST /api/v1/admin/api-key/rotate`, same
  `require_admin_mfa_permission` gate as the other two admin actions.
  Returns `secrets.token_urlsafe(32)` directly in the response body — never
  written to DB or audit metadata (the self-audit entry,
  `admin.api_key.rotate_candidate_generated`, has empty `{}` metadata by
  design, confirmed live). Response includes plain-language activation
  instructions.
- Frontend: `lib/api.ts` adds `rotateApiKeyCandidate()`. New
  `components/ApiKeyRotatePanel.tsx`, same one-component-per-admin-action
  pattern as Sprints 26-27, mounted between `AdminAuditExport` and
  `DangerZone` in `SettingsPanel.tsx`. `AdminAuditExport`'s card header
  renamed from generic "Admin Tools" to "Export Audit Log" now that three
  distinct admin cards exist side by side.
- Verified: backend `pytest -q` => 309 passed (up from 304: 5 new tests).
  `ruff` clean. Frontend `tsc --noEmit` clean; `npm run build` success.
  **Live browser verification**: wrong TOTP code → "Invalid TOTP code"
  inline, console showed only the expected `403` (no CORS issue — nothing
  new needed there). Real TOTP code → real key displayed once with
  instructions, cross-checked directly against the backend audit log
  (`metadata: {}`, key confirmed never persisted). Verification processes
  cleaned up, `.env.local` reverted, scratch DB removed.
- Explicitly still out of scope: live/automatic key cutover (needs Vault
  actually deployed + a Vault-write path — real infrastructure work, not
  started opportunistically here); "manage JWT role config" (distinct
  question — this service has no user/role database, only env-configured
  role-name lists; still not addressed).

2026-08-14 — Sprint 29 opened and closed: frontend can now authenticate (X-API-Key):

- New planning board: `docs/planning/SPRINT29_TASK_BOARD.md`. User asked
  what remained manual for an end user of the app; a long-flagged inherited
  gap surfaced again ("frontend never sends X-API-Key"), meaning a backend
  deployed with real auth enforced could never be used through the web
  UI — only via direct API calls. User picked this to fix over the
  alternative (Google Calendar multi-calendar support, which turned out
  non-trivial on inspection: `"google_calendar"` is hardcoded as a single
  source key across the capabilities matrix, the Sidebar color map, and the
  manual sync endpoint path).
- `frontend/src/lib/api.ts`: added `getStoredApiKey()`/`setStoredApiKey()`
  (`localStorage`-backed, SSR-safe) and a `baseHeaders(extra?)` helper.
  Every exported fetch function (~18 of them) now builds its headers via
  this helper instead of an inline object, so `X-API-Key` is attached
  automatically whenever a key is stored — done as a mechanical, file-wide
  edit. No backend changes needed at all: `X-API-Key` was already fully
  supported and already CORS-whitelisted; only the frontend's failure to
  send it was the gap.
- New `frontend/src/components/ApiKeySettings.tsx`: "Backend Access" card
  in Settings, placed after Workspace and before Connected Sources (it's
  about the browser's own auth, not an admin-only action, so kept separate
  from the TOTP-gated admin cards). Loads the persisted value via a
  mount-only `useEffect` (not a `useState` initializer) — following the
  Sprint 11 hydration-mismatch lesson exactly.
- Also this session: re-ran `pip-audit` and `npm audit` as a housekeeping
  check (last run at Sprint 9) — both clean, no CVEs, nothing to remediate.
- **Accepted tradeoff, stated not hidden**: the key is stored in
  `localStorage` (not `sessionStorage`), chosen for login-like persistence
  across restarts; this is more exposed to XSS than a proper `httpOnly`
  session cookie, judged acceptable for this project's local-first,
  single-operator posture — revisit if this app is ever exposed multi-user
  over the open internet.
- Verified: frontend `tsc --noEmit` clean; `npm run build` success. Backend
  `pytest -q` => 309 passed (unchanged, pure frontend change). **Live
  browser verification against a backend with auth genuinely enforced**
  (`ALLINO_ALLOW_INSECURE_DEV=false`, real `ALLINO_API_KEY` set — a first;
  every prior live-verification session had used insecure-dev mode): no
  key stored → real `401`s everywhere, handled gracefully by existing
  error-state UI; entered + saved the key → confirmation shown; reloaded →
  key persisted, all panels loaded real data, zero console errors; cleared
  the key → `401`s reappeared immediately on next fetch, confirming the
  header is read fresh per-request, not cached. Verification processes
  cleaned up, `.env.local` reverted, scratch DB removed.
- Explicitly still out of scope: a real login screen / JWT issuance from
  this app (unchanged by design — this app only verifies externally-issued
  JWTs); Google Calendar multi-calendar support (deferred, needs its own
  scoping pass).

2026-08-14 — Sprint 30 opened and closed: auto-sync for built-in connectors + sync-now button + TOTP QR enrollment + activity digest:

- New planning board: `docs/planning/SPRINT30_TASK_BOARD.md`. User asked for
  a readiness assessment, then asked for four improvements in one pass
  (auto-sync, sync-now, TOTP QR, digest); a fifth (local AI classifier via
  Ollama) was explicitly separated out as its own future sprint (new
  infrastructure, not incremental code), and WhatsApp/Viber was explicitly
  deferred again mid-session by the user.
- **Auto-sync for built-in connectors**: `ALLINO_BUILTIN_CONNECTORS_POLL_*`
  env vars (same single-env-tenant shape as Google Calendar polling,
  Sprint 19). `services/connector_sync.py` gained `sync_builtin_connector()`
  (reuses the existing `record_batch_result()` helper — no new telemetry
  logic). `workers/scheduler_worker.py` now attempts GitHub/GitLab/Jira/
  Linear/Telegram/Slack/Discord/Zoom/Teams/Rocket.Chat, skipping any source
  whose secret isn't configured. **Found and fixed a real deployability
  gap**: `docker-compose.yml` never forwarded ANY of the 10 built-in
  connector token env vars to the `backend`/`scheduler_worker` services
  (only Wave 2's were even documented in `.env.example` — Wave 1's
  GitHub/GitLab/Jira/Linear/Telegram/Slack tokens were never wired at all).
  Fixed both files; also added the previously-missing
  `ALLINO_ADMIN_TOTP_SECRET` forward to `docker-compose.yml`.
- **"Sync now" button**: `SettingsPanel.tsx`'s Connected Sources rows now
  have a manual sync button when a source is available+configured+
  sync_supported. This changes a guardrail noted in earlier sprints ("no
  manual sync now button — deliberate pattern") — that pattern is now
  retired by explicit user request, not silently reversed.
- **TOTP QR enrollment**: deliberately NOT a server endpoint — an endpoint
  that could hand back the raw TOTP seed would let any API-key holder
  permanently self-enroll a device and bypass the second factor Sprint 26
  built. Instead: `backend/scripts/generate_admin_totp_qr.py`, a local-only
  CLI script (otpauth URI + ASCII QR in the terminal, or `--output` for a
  PNG). Found and fixed a real Windows-only bug: `qrcode`'s ASCII output
  uses Unicode block characters that Windows' default console codepage
  can't encode — fixed via `sys.stdout.reconfigure(encoding="utf-8")`.
- **Activity digest**: `GET /api/v1/ingestion/digest?hours=24` — pure
  rule-based aggregation (counts by source/priority + top-10 high-priority
  highlights) over `messages.created_at` (ingestion time, not source
  timestamp). Zero AI, zero new runtime dependencies. New
  `components/DigestPanel.tsx`, a third content-swap state in `page.tsx`
  alongside Archived/Search (ClockIcon button), same mutual-exclusion
  convention those two already use. Not a 6th L1 nav section.
- Verified: backend `pytest -q` => 324 passed (up from 309: 7 scheduler +
  6 digest + 2 TOTP-script tests). `ruff` (exact CI scope) clean. Frontend
  `tsc --noEmit` clean; `npm run build` success. `docker-compose.yml`
  re-validated as parseable YAML. **Live verification**: scheduler
  auto-sync run as a real subprocess three times (0-tokens-configured →
  0 syncs; 1 invalid token configured → real HTTP call to api.github.com,
  real 401, captured gracefully without crashing); Sync-now button and
  Digest panel both live-verified in a real browser (zero unexpected
  console errors); TOTP QR script run for real, including the Windows
  encoding fix. Verification processes cleaned up, `.env.local` reverted,
  scratch DBs removed.
- Explicitly still out of scope: local AI priority classifier (Ollama) —
  separated out on purpose, needs its own sprint (new inference service,
  not incremental code); WhatsApp/Viber (still deferred); multi-tenant
  auto-sync for built-ins (same single-env-tenant limitation as Google
  Calendar polling — no persisted per-tenant connector-config table exists
  for built-ins).

2026-07-04 — Sprint 31 opened and closed: multi-tenant auto-sync for
built-in connectors, plus the project's first git repo and a persistent
local prod/dev split:

- User picked this item from the known-gaps list (WhatsApp/Viber, local AI
  classifier, multi-tenant auto-sync) via `AskUserQuestion`. A real fork
  came up before writing code: how to store a second/third tenant's own
  GitHub/Jira/etc. credentials, since these previously only came from
  global env vars. Asked the user directly; picked **encrypted DB
  storage** (new `builtin_connector_secrets` table, Fernet-encrypted JSON
  blob via the existing `core/crypto.py`, same envelope as
  `messages.preview`) over the env-var-per-tenant-naming alternative.
- New: migration `0019_builtin_connector_secrets.sql`,
  `db/repositories/builtin_connector_secrets_repo.py`,
  `api/builtin_connector_secrets.py` (`POST/DELETE
  .../builtin/{source_type}/secret`, `GET .../builtin/secrets` — never
  returns decrypted tokens, only `configured: true`). Covers all 10
  built-in named connectors plus `google_calendar` (11 source types) in
  one table.
- `workers/scheduler_worker.py`: new loop over
  `list_builtin_connector_secrets_with_polling()`, keyed by the same
  `f"{tenant_id}:{source}"` due-check as the pre-existing single-env-tenant
  path. The legacy env path (`ALLINO_BUILTIN_CONNECTORS_POLL_*`) is kept,
  not replaced — deployments relying on it still work — but now skips any
  `(tenant_id, source)` pair that already has a DB-configured row, so a
  tenant is never double-synced.
- Frontend: new `components/BuiltinConnectorSecretsPanel.tsx` ("Your Own
  Credentials"), mounted in `SettingsPanel.tsx` above `GenericConnectorsPanel`.
  Fixed outdated "secrets are never entered through this UI" copy in both
  `SettingsPanel.tsx` and `OnboardingScreen.tsx` — no longer true.
- Tests: 5 repo + 8 API + 5 scheduler tests, all in the existing sibling
  test files' style. Backend: `pytest -q` => 396 passed (up from 324).
  `ruff check app tests --select F,E9` clean. Frontend `tsc --noEmit` and
  `npm run build` clean.
- **Real scheduler subprocess verification**: stored a real-but-invalid
  GitHub token via the new API, ran `python -m app.workers.scheduler_worker
  --once` for real — genuine HTTP call to `api.github.com`, real `401`,
  captured gracefully in the connector registry without crashing.
- **Live browser verification found a real dev-mode-only bug**: in `next
  dev`, clicking "Settings" updated `aria-current` on the nav button but
  the Inbox 3-pane layout kept rendering instead of `SettingsPanel` — no
  app-code bug, confirmed by switching to a production build (`next build
  && next start`), where Settings navigation and the new panel worked
  correctly on the first try. Matches this project's known "dev-mode HMR
  through the sandbox's docker bridge produces app-shaped symptoms" class
  of quirk (see the Sprint 9 entry above). Configured + edited + deleted a
  GitHub secret through the real UI; zero real console errors.
- **Separately this session, at the user's request**: the project had no
  git repository at all despite 30 prior sprints. Initialized one
  (`git init -b main`, first commit = the full working tree, 274 files —
  `.gitignore` already correctly excluded secrets/DBs/`node_modules`/
  `.venv`, verified before committing). Created a `dev` branch via `git
  worktree add ../ALLinO-dev -b dev`; this sprint's frontend half was built
  there, on its own Python venv and SQLite DB, so it never touched the
  user's running instance. Added `restart: unless-stopped` to every
  `docker-compose.yml` service (none had one before — the stack would not
  have survived a host reboot). Generated a real `ALLINO_API_KEY` +
  `ALLINO_ENCRYPTION_KEY` into a git-ignored root `.env`, then `docker
  compose up -d --build` — confirmed all 5 services healthy, `/health`
  returns `ok`, auth enforced. **Promotion model going forward**: user says
  "перенеси" (or equivalent) → merge `dev` into `main` in the primary
  worktree → `docker compose up -d --build`. Nothing pushed anywhere; this
  is entirely local. See `docs/planning/SPRINT31_TASK_BOARD.md` for the
  full narrative including the two `AskUserQuestion` forks.

2026-07-04 — Channel-browser grouping extended to Telegram; full-user-access
Telegram explicitly deferred:

- Rocket.Chat already had a "grouped by Teams/Channels/Direct messages"
  Inbox view (`ChannelBrowser.tsx`/`ChannelTranscript.tsx`, a
  `channel_kind` field on messages, `/channels` API) predating this
  project's own tracked sprint history — built in an earlier untracked
  session, not documented until now. Extended it to Telegram:
  `map_telegram_update_to_unified_event` now classifies `chat.type`
  ("private" -> `dm`; group/supergroup/channel -> `channel` — Telegram has
  no team/workspace concept like Slack/Rocket.Chat, so this is a two-way
  split not three-way), and `telegram` was added to the frontend's
  `CHAT_SHAPED_SOURCES`. The normalizer/`/channels` API needed zero
  changes — already fully source-agnostic.
- **Full user-account access to Telegram (MTProto/"userbot" login,
  equivalent to logging into the account from another device) was
  explicitly discussed and deferred by the user**, not silently skipped.
  User asked directly why Rocket.Chat's own token (which grants comparably
  broad access within its instance) wasn't treated with the same alarm —
  fair challenge. The real distinguishing factor, explained and accepted:
  Rocket.Chat's Personal Access Token is a platform-sanctioned, scoped,
  independently-revocable delegated-access mechanism, built by Rocket.Chat
  specifically for third-party integrations. Telegram has no equivalent
  mechanism for personal accounts — an MTProto user session is not
  delegated access, it's the same login primitive the official client
  uses, with no partial-scope or independent revocation, and carries
  additional Telegram ToS/automation-detection risk that a sanctioned API
  token does not. **Decision, not a technical blocker**: the user accepted
  Bot API's limits (no visibility into personal DMs with other people,
  can't see channel/group history before the bot was added) for now.
  Revisit only on an explicit future request — if picked up, expect a
  genuinely new connector architecture (interactive phone+code login flow,
  session-string storage, its own security review), not an incremental
  extension of `TelegramConnector`.
- **Same-day follow-up**: user asked specifically about QR-code login
  (scan with phone, like Telegram Desktop/Web) instead of phone+SMS-code,
  wondering if that changes the risk. Answered honestly: no — QR login is
  a real, legitimate Telegram authentication method (and libraries like
  Telethon/Pyrogram support it), but it's a different way to *establish*
  the same full-account MTProto session, not a smaller-scope one. Same
  leak consequences, same single-revocation-point ("Active Sessions" in
  Telegram itself), same ToS/automation-detection exposure; Telegram's own
  2FA password prompt (if the account has one) applies identically
  regardless of QR vs. phone+code, it's not something ALLinO would add on
  top. User was given the real scope of building this (live QR-display UI,
  polling for phone approval, 2FA password handling, encrypted session
  storage — a new connector architecture, not a token field) and explicitly
  chose to stay on Bot API rather than start it now.

## 5) What to read first in a new session

1. ../../CLAUDE.md
2. ../../PROJECT_MASTER_BRIEF.md (sections 1.2, 1.3, 1.4)
3. ./PREBUILD_SPEC_V1.md
4. ./SPRINT_PLAN_W1_W2.md
5. ./SPRINT31_TASK_BOARD.md (most recent closed board — Sprint 1-30 boards are historical)
6. ./RELEASE_HARDENING_CHECKLIST_S6.md
7. ./AGENT_START_TEMPLATE.md
8. this file (CURRENT_STATE.md), especially the "Open items" note under section 4

## 6) Guardrails for next agents

- **Read this bullet first — supersedes the Sprint 30 bullet immediately
  below it**: Sprint 31 (2026-07-04) is the most recently closed board.
  Built-in connector auto-sync is now genuinely multi-tenant: a
  `builtin_connector_secrets` DB table (Fernet-encrypted config blob, same
  as `messages.preview`) lets any tenant bring their own token for
  GitHub/GitLab/Jira/Linear/Telegram/Slack/Discord/Zoom/Teams/Rocket.Chat/
  Google Calendar, managed via `api/builtin_connector_secrets.py` and a new
  "Your Own Credentials" panel in Settings. The old single-env-tenant path
  (`ALLINO_BUILTIN_CONNECTORS_POLL_*`) still works unchanged for whichever
  tenant it names, but is now skipped for any `(tenant_id, source)` pair
  that also has a DB row, so there's no double-sync. **Also as of this
  sprint: the project has a real git repository** (`git init` on `main`,
  first commit was the pre-Sprint-31 tree). Ongoing work happens in a `dev`
  branch/worktree (`git worktree add ../ALLinO-dev -b dev`); the primary
  directory is reserved for `main`, which is what the persistent
  `docker-compose` "prod" stack is built from. Promotion is user-triggered
  ("перенеси") — merge `dev` → `main`, then `docker compose up -d --build`.
  A root `.env` (git-ignored) holds the real `ALLINO_API_KEY` +
  `ALLINO_ENCRYPTION_KEY` for that stack; don't regenerate these without
  telling the user, since the frontend's stored key (Sprint 29,
  `localStorage`) would stop matching.
- Sprint 30 (2026-08-14) is the previously-most-recent board —
  built-in connectors (GitHub/GitLab/Jira/Linear/Telegram/Slack/Discord/Zoom/
  Teams/Rocket.Chat) now auto-sync via the scheduler worker
  (`ALLINO_BUILTIN_CONNECTORS_POLL_*`, single-env-tenant scoped like Google
  Calendar polling), each source only attempted if its secret is configured.
  `docker-compose.yml` now actually forwards all 10 connector tokens (it
  never did before — a real pre-existing deployability gap, not something
  Sprint 30 introduced). Settings' Connected Sources rows now have a
  "Sync now" button — the older "no manual sync button, deliberate pattern"
  guardrail from earlier sprints is retired by explicit user request, not a
  silent reversal. TOTP enrollment now has a QR code via a **local-only CLI
  script** (`backend/scripts/generate_admin_totp_qr.py`) — deliberately NOT
  a server endpoint (would let any API-key holder bypass the 2nd factor
  permanently). A rule-based (non-AI) activity digest exists at
  `GET /api/v1/ingestion/digest` + a `ClockIcon` button in the Inbox header.
  Sprint 29 fixed "frontend never sends X-API-Key" (`ApiKeySettings.tsx`,
  `baseHeaders()` in `lib/api.ts`). Three admin actions exist under
  `/api/v1/admin`, all behind `require_admin_mfa_permission`:
  delete-all-tenant-messages (S26), export-tenant-audit-log (S27), and
  rotate-API-key-candidate (S28, a **candidate generator only** — see that
  board for why live rotation isn't possible without Vault actually
  deployed). Manage-JWT-role-config and a local AI priority classifier
  (Ollama) are both still deferred, each needing its own sprint (no
  user/role DB exists at all; local AI needs a new inference service, not
  incremental code).
  the paragraphs immediately below are stale leftovers from when they were
  current and are kept for their still-valid reasoning, not their "most
  recent" framing. No Sprint 21 board exists yet — open one before starting
  new work. A scheduler worker DOES now exist (`backend/app/workers/
  scheduler_worker.py`, Sprint 18) but it is narrowly scoped: Generic HTTP
  Connectors (via their `poll_interval_seconds` DB column) plus, as of Sprint
  19, exactly one env-configured Google Calendar tenant/calendar
  (`ALLINO_GOOGLE_CALENDAR_POLL_*`). It does **not** auto-poll any other
  built-in connector (Zoom/Teams/Slack/GitHub/etc.) — don't assume "we have a
  scheduler" means every connector auto-syncs. The `.icon-btn` text-overflow
  bug (originally just the "+ Add connector" button) was fixed in Sprint 20 —
  turned out to be 3 occurrences, not 1; see that board before assuming any
  other `.icon-btn` usage is safe without checking it's a single-icon button.
  Onboarding (`OnboardingScreen.tsx`) was added in Sprint 21. Archive/Snooze
  (`ThreadPanel.tsx`) were wired up for real in Sprint 22. Snooze got a
  duration picker in Sprint 23. "View archived" + Unarchive shipped in
  Sprint 24. Search shipped in Sprint 25 (exact substring match, not FTS —
  see that board for why: `messages.preview` is encrypted at rest, a real
  FTS index would mean persisting a plaintext-searchable copy of message
  content, a security regression the user didn't ask for). Admin MFA
  (TOTP step-up, `core/security.py:require_admin_mfa_permission`) +
  "delete all tenant messages" (`api/admin.py`, `Settings` → Danger Zone)
  shipped in Sprint 26 — `CLAUDE.md` §4's "MFA for admin paths" line is no
  longer an unimplemented aspiration. `/api/v1/admin` is the pattern for
  any future admin action. `CORSMiddleware.allow_headers` now includes
  `X-TOTP-Code` — remember to extend `allow_headers` (not just
  `allow_methods`, see the Sprint 16 lesson) when a future endpoint adds
  its own custom auth header. `tests/conftest.py` now also clears
  `rate_limit.RATE_LIMITER` before every test — if you see order-dependent
  rate-limit-related test failures again despite that, look for a *second*
  shared singleton, not assume this fix regressed.
- Do not edit docs/agent-answers/incoming/\* unless explicitly requested.
- Keep security-first/privacy-first/local-first/read-first constraints intact.
- Wave 1 (core + optional) and Wave 2 connector coverage is now complete:
  GitHub, GitLab, Jira, Linear, Telegram, Slack, Discord, Zoom, Teams, Google
  Calendar (10 total). Do not start Wave 3 (Rocket.Chat, WhatsApp Business,
  Viber) without an explicit sprint board for it.
- Sprint 17 closed (S17-01/S17-02: reply extended to GitHub/GitLab/Jira/
  Linear + `messages.reply_target` column; see the 2026-07-02 Sprint 17
  changelog entry). No Sprint 18 board exists yet — open one before
  starting new work rather than assuming scope. Reply/write-back is now
  live for 8 of 11 built-in connector sources (Telegram, Slack, Discord,
  Rocket.Chat, GitHub, GitLab, Jira, Linear). Remaining known gaps as of
  this writing (not started): WhatsApp Business and Viber (Wave 3's other 2
  sources — webhook-push-only APIs, building either needs a new built-in
  webhook-receiver connector shape, a real architecture decision; each
  needs its own board); Google Calendar push/watch-channel support +
  renewal cron (needs new scheduler infrastructure this project doesn't
  have for any connector yet); reply for Zoom/Teams (meeting-shaped, no
  reply semantics — Google Calendar excluded for the same reason); renaming
  a Generic HTTP Connector / changing its slug (left immutable — see
  Sprint 16 board for why); manual "sync now" trigger from the UI for any
  connector (deliberate pattern, not a gap).
- **`messages.reply_target` column (added Sprint 17):** nullable, encrypted
  at rest like `preview`. Only populated for GitHub (`subject_url`) and
  GitLab (`target_url`) — every other source either doesn't support reply
  or has everything it needs already in `external_id`. If extending reply
  to a new issue-tracker-shaped source in the future, check first whether
  its `external_id` is already sufficient (Jira/Linear pattern) before
  assuming a new persisted field is needed (GitHub/GitLab pattern) — don't
  default to the more complex path.
- **CORS gotcha for future write endpoints:** `backend/app/main.py`'s
  `CORSMiddleware.allow_methods` is an explicit whitelist, not `["*"]`
  (intentional, from earlier security hardening). Adding any new HTTP
  method (e.g. `PUT`, or reusing `PATCH` again) to a router requires adding
  it to this list too, or the browser's CORS preflight will fail silently
  from `pytest`'s perspective — `TestClient` doesn't execute real preflight
  checks, so this only surfaces as a real browser console error during live
  verification. See `backend/tests/test_cors_methods.py` for the regression
  test pattern (assert `OPTIONS` preflight response includes the method in
  `Access-Control-Allow-Methods`) — extend it, don't just re-discover this
  live again, when adding the next write method.
- When verifying a frontend change live in a browser in this sandbox, the
  browser-automation container cannot resolve `localhost` back to the host
  machine. Point `NEXT_PUBLIC_BACKEND_URL` at `http://host.docker.internal:8000`,
  bind uvicorn with `--host 0.0.0.0`, and add the `host.docker.internal:3000`
  origin to `ALLINO_ALLOWED_ORIGINS` — then rebuild. Revert the env var when
  done (it's a local dev convenience, not a real config change). Also: `pkill`
  from this shell does not reliably kill Windows-native `uvicorn`/`next`
  child processes, which can silently leave a stale process holding the old
  port/config while a new one also binds successfully — if CORS/URL fixes
  don't seem to take effect, check `netstat -ano | grep LISTENING` for
  duplicate listeners on the same port and `taskkill //PID <pid> //F` the
  stale one. See the Sprint 12 changelog entry for how this actually surfaced.
- When verifying a frontend change live in a browser (mandatory per
  CLAUDE.md §6) and a `useState` initializer reads `sessionStorage`/
  `localStorage`, check specifically for a hydration mismatch by setting a
  non-default persisted value first (`sessionStorage.setItem(...)` via
  `browser_evaluate`) before reloading — the default/empty-storage case will
  not surface this class of bug. See the Sprint 11 changelog entry for a
  concrete example (`page.tsx`'s `mode`/`filters` state) and the fix pattern
  (SSR-safe default in `useState`, restore via a mount-only `useEffect`).
- If verifying a frontend change live in a *dev server* (`next dev`) inside a
  sandboxed/containerized browser-automation tool and data fetching hangs
  indefinitely (e.g. stuck on a loading state) with no console/network errors
  explaining why: check whether it reproduces in **production mode**
  (`next build && next start`) before assuming an app-code bug — a dev-mode
  HMR WebSocket handshake failing through a docker network bridge can produce
  exactly this symptom and is specific to the sandbox, not the app. See the
  Sprint 9 changelog entry above for the full diagnosis.
- Before adding new tenant-data-reading endpoints, re-read `core/tenant.py`:
  JWT-authenticated callers are tenant-bound to their claim; API-key callers
  are treated as trusted operational/cross-tenant callers by design. Don't
  assume the header/query tenant_id is authoritative for JWT callers.
- Run `ruff check app tests --select F,E9` before closing out a session — this
  is the exact CI lint gate, and unused-import regressions have slipped through
  before (see 2026-07-01 lint fix entry above).
- Keep changes minimal and update task board + this handoff file after meaningful execution changes — write the changelog entry as you go, not at the end of the session, so an interrupted session (e.g. running out of budget) doesn't leave undocumented work behind.
