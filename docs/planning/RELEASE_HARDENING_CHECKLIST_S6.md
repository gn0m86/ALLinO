# ALLinO Sprint 6 Release Hardening Checklist

Date: 2026-07-01
Scope: post-S6 verification snapshot.

## 1) Wave 2 Integration Coverage

- [x] Zoom connector implemented (`/connectors/zoom/sync`) with mapping + endpoint tests.
- [x] Teams connector implemented (`/connectors/teams/sync`) with mapping + endpoint tests.
- [x] Connector exports and ingestion routing include Zoom and Teams.

## 2) Runtime Capability Matrix

- [x] Capabilities matrix marks `zoom` and `teams` as `available=true` and `sync_supported=true`.
- [x] Runtime `configured` flags remain env-driven for both connectors.
- [x] Secret requirement semantics remain explicit (`requires_secret=true`).

## 3) Frontend Readiness Signals

- [x] Sources panel includes Zoom/Teams via capability-driven rendering.
- [x] `setup` indicator remains visible for connectors with `configured=false`.
- [x] Existing connector telemetry and status rendering remained stable.

## 4) Smoke + Quality Gates

- [x] Smoke runbook extended with Zoom seeded sync scenario.
- [x] Smoke runbook extended with Teams seeded sync scenario.
- [x] Backend suite passes after Sprint 6 updates (`pytest -q` => 97 passed).
- [x] Frontend build passes after Sprint 6 updates (`npm --prefix frontend run build` => success).

## 5) Reliability Hardening (post-S6)

- [x] Zoom retry behavior covered (recoverable transient failures + retry exhaustion).
- [x] Teams retry behavior covered (recoverable transient failures + retry exhaustion).
- [x] Zoom/Teams sync error paths validated for registry/run persistence (`status=error`, error details stored).
- [x] Retry policy hardened to fail-fast on non-retryable HTTP 4xx (except 429), while keeping retries for 429/5xx.
- [x] Endpoint-level fail-fast contract validated for provider `401` on Zoom/Teams sync (`502` + single provider attempt + error persistence).
- [x] Runtime retry controls added on sync endpoints (`retry_max_attempts`, `retry_backoff_seconds`) with validated bounds and integration coverage.
- [x] Connector token accepted only via `X-Connector-Token` header (body fallback removed).
- [x] Event-bus async worker path has retry + fallback controls (`ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS`, timeout fallback) with test coverage.

## 6) Go / No-Go

Current assessment: GO for continued Wave 2 delivery baseline.

Before production cut:

1. Execute Zoom + Teams smoke scenarios in staging with real secrets/scopes.
2. Validate token scopes/permissions for provider APIs in each environment.
3. Add targeted retry/error contract tests for provider API failures (401/429/5xx) before production onboarding.

Execution aids:

1. Staging readiness protocol: `docs/planning/STAGING_READINESS_PACK_S6.md`.
2. Evidence template: `docs/planning/STAGING_SMOKE_EVIDENCE_TEMPLATE.md`.
3. Automation script: `backend/scripts/staging_smoke_wave2.ps1`.
4. Evidence validator: `backend/scripts/validate_staging_smoke_wave2.py`.
5. One-command release gate: `backend/scripts/release_gate_wave2.ps1`.
6. External worker DLQ smoke (required in strict mode): `backend/scripts/staging_smoke_external_worker_dlq.py`.
7. Strict DLQ preflight (required in strict mode): `backend/scripts/preflight_external_worker_dlq.py`.
8. Release report validator: `backend/scripts/validate_release_gate_wave2_report.py`.
9. Evidence bundle builder: `backend/scripts/build_release_evidence_bundle.py`.
10. Release handoff generator: `backend/scripts/generate_release_handoff_wave2.py`.
11. Artifacts redaction script: `backend/scripts/redact_release_artifacts.py`.

## 7) Security Gate Regression Check (cross-sprint)

- [x] Tenant binding for JWT callers is claim-based (`tenant_id`/`tenantId`/`tid`), with mismatch rejection.
- [x] Insecure dev mode is explicit opt-in (default `ALLINO_ALLOW_INSECURE_DEV=false`).
- [x] Compose path is fail-closed oriented (`ALLINO_ENV=production`, `ALLINO_ALLOW_INSECURE_DEV=false`).
- [x] Rate limiting for ingestion/auth path implemented (middleware + env-config + tests for `429`).
- [x] Encryption-at-rest baseline implemented for sensitive persisted fields (app-level encryption for metadata/preview/error strings, with tests).
- [ ] Full database/file encryption is still not implemented (SQLite file remains plaintext at storage layer).
- [x] CSP/HSTS header policy implemented in backend + frontend runtime config (middleware/Next headers + tests + build validation).
- [x] Vault-backed secret lookup implemented (env-first, Vault KV v2 fallback for auth/connector/encryption secrets, with tests).
- [ ] External Vault infrastructure is not provisioned in this repository (runtime integration ready, ops provisioning pending).
- [x] Event-bus consumer baseline now includes async worker mode (separate consumer thread path), reducing same-call round-trip coupling.
- [x] External event-bus worker process baseline added (Redis request/result path + dedicated worker entrypoint, opt-in by env).
- [x] External worker hardening added: retry/backoff + DLQ path + worker healthcheck + release-gate strict mode (`-RequireExternalWorker`).
- [x] Release gate supports strict DLQ evidence mode (`-RequireExternalWorkerDlq`) with dedicated DLQ smoke artifact.
- [x] Strict DLQ mode runs preflight checks (env + redis reachability) and records preflight artifact in report.
- [x] Release gate now runs report validator automatically and stores validator log/exit-code in release report.
- [x] Release gate now builds evidence bundle manifest+summary and stores bundle paths in release report.
- [x] Release gate now generates handoff markdown and stores handoff path/log in release report.
- [x] Release gate now runs artifacts redaction and stores redaction manifest/sanitized dir paths in release report.
