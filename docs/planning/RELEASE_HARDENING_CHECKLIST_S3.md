# ALLinO Sprint 3 Release Hardening Checklist

Date: 2026-07-01
Scope: post-S3-07 baseline verification snapshot.

## 1) Security Checklist

- [x] Auth fail-closed mode present (`ALLINO_API_KEY` / `ALLINO_JWT_SECRET` policy).
- [x] JWT connector sync permission policy enforced.
- [x] JWT ingestion read permission policy enforced.
- [x] Tenant-scoped read paths verified (`inbox`, `audit`, `stats`, `metrics`, `connectors`, `connectors/runs`).
- [x] Audit append-only DB triggers present.
- [x] Token sanitization on rejected-event logging paths.

## 2) Data and Migration Safety

- [x] Migration tracking table (`schema_migrations`) in use.
- [x] Connector telemetry migration applied (`0006_connectors_telemetry.sql`).
- [x] Thread key migration applied (`0007_thread_key.sql`).
- [x] Connector runs migration applied (`0008_connector_runs.sql`).
- [x] Inbox cursor API added without breaking existing `/inbox` contract.

## 3) Integration and Runtime

- [x] Core connectors active: GitHub, GitLab, Linear.
- [x] Sprint 3 connectors added: Jira, Telegram.
- [x] Connector capability matrix endpoint available: `/api/v1/ingestion/connectors/capabilities`.
- [x] Event-bus start path present and feature-flagged (`ALLINO_EVENT_BUS_ENABLED`).

## 4) CI and Quality Gates

- [x] Backend CI has Python matrix (3.12, 3.13).
- [x] Frontend CI has Node matrix (20, 22).
- [x] CI artifacts retained for debugging (test report and build/typecheck logs).
- [x] Backend lint includes `F,E9` safety/syntax checks.

## 5) Current Verification Evidence

- [x] Backend tests: `pytest -q` -> `78 passed`.
- [x] Frontend build: `npm --prefix frontend run build` -> success.

## 6) Go / No-Go

Current assessment: GO for continued Sprint 3 execution baseline (development/staging track).

Conditions before production cut:

1. Complete remaining Sprint 3 board tasks and re-run full smoke in staging.
2. Validate Redis-backed event-bus mode in environment with reachable Redis.
3. Freeze env var set and secrets management for deployment target.
