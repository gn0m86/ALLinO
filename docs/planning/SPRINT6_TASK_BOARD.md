# ALLinO Sprint 6 Task Board

Статус: Completed
Дата старта: 2026-07-01
Длительность: 5 рабочих дней (или 10 при part-time)

## Цель спринта

Перевести Wave 2 источники Zoom и Teams из readiness-флагов в реальный sync read-path с тестами и актуальным smoke/runbook.

## Правила работы

1. Security-first baseline из Sprint 4/5 сохраняется без ослаблений.
2. Новые интеграции закрываются только с endpoint + mapping + тестами + документацией.
3. Capability matrix и UI должны отражать фактическую доступность sync.

---

## Board (состояния)

### Ready

- [x] S6-01 Реализовать Zoom connector end-to-end.
- [x] S6-02 Реализовать Teams connector end-to-end.
- [x] S6-03 Обновить smoke runbook сценариями Zoom/Teams sync.
- [x] S6-04 Добавить Sprint 6 release checklist snapshot.

### In Progress

- [ ] (нет активных задач)

### Done

- [x] S6-01 Zoom connector end-to-end.
- [x] S6-02 Teams connector end-to-end.
- [x] S6-03 Smoke runbook expanded for Zoom/Teams sync.
- [x] S6-04 Sprint 6 release hardening checklist snapshot.

### Blocked

- [ ] (блокеры и зависимости)

---

## Sprint 6 Exit Criteria

1. Zoom endpoint доступен и покрыт тестами.
2. Teams endpoint доступен и покрыт тестами.
3. Capabilities endpoint отражает Zoom/Teams как sync-supported.
4. Sources UI показывает Zoom/Teams и setup-indicator для не сконфигурированных источников.
5. Smoke runbook и release checklist синхронизированы с реализацией.

---

## Журнал решений

- 2026-07-01: Sprint 6 board создан для Wave 2 execution.
- 2026-07-01: S6-01 закрыт. Добавлены `zoom_connector.py`, endpoint `/api/v1/ingestion/connectors/zoom/sync`, тесты `test_zoom_connector.py`, `test_zoom_sync_endpoint.py`.
- 2026-07-01: S6-02 закрыт. Добавлены `teams_connector.py`, endpoint `/api/v1/ingestion/connectors/teams/sync`, тесты `test_teams_connector.py`, `test_teams_sync_endpoint.py`.
- 2026-07-01: S6-03/S6-04 закрыты. Runbook дополнен Zoom/Teams sync, добавлен `RELEASE_HARDENING_CHECKLIST_S6.md`.
- 2026-07-01: Финальная валидация Sprint 6: backend `pytest -q` => 91 passed; frontend `npm --prefix frontend run build` => success.
- 2026-07-01: Post-S6 hardening: добавлены негативные/retry тесты для Zoom/Teams (connector + sync error-path persistence), backend `pytest -q` => 97 passed.
- 2026-07-01: Retry policy hardening: fail-fast на non-retryable HTTP 4xx (кроме 429), дополнительные code-specific тесты Zoom/Teams; backend `pytest -q` => 101 passed.
- 2026-07-01: Endpoint-level fail-fast coverage: добавлены API тесты Zoom/Teams на provider 401 (single attempt + 502 + error persistence), backend `pytest -q` => 103 passed.
- 2026-07-01: Runtime retry controls: sync endpoints принимают `retry_max_attempts` и `retry_backoff_seconds` с валидацией и интеграционными тестами; backend `pytest -q` => 106 passed.
- 2026-07-01: Staging readiness pack подготовлен: `STAGING_READINESS_PACK_S6.md`, `STAGING_SMOKE_EVIDENCE_TEMPLATE.md`, `backend/scripts/staging_smoke_wave2.ps1`.
- 2026-07-01: Added evidence validator `backend/scripts/validate_staging_smoke_wave2.py` + tests `test_staging_smoke_validator.py`; backend `pytest -q` => 110 passed.
- 2026-07-01: Added one-command release gate orchestrator `backend/scripts/release_gate_wave2.ps1` (smoke + validate + report + GO/NO-GO exit code).
- 2026-07-01: Project Review #2 critical fixes applied: JWT tenant claim binding + safer auth defaults + permission dependency hardening; backend `pytest -q` => 115 passed.
- 2026-07-01: Project Review #2 follow-up: implemented ingestion/auth path rate limiting (middleware + env config + tests), backend `pytest -q` => 117 passed.
- 2026-07-01: Project Review #2 follow-up: implemented CSP/HSTS + browser security headers for backend/frontend runtime (middleware + Next headers + tests), backend `pytest -q` => 120 passed; frontend build => success.
- 2026-07-01: Project Review #2 follow-up: implemented encryption-at-rest baseline (field-level encryption for sensitive DB strings + production key guard + tests), backend `pytest -q` => 123 passed.
- 2026-07-01: Project Review #2 follow-up: implemented Vault-backed secrets baseline (env-first + Vault KV v2 fallback for auth/connector/encryption secrets), backend `pytest -q` => 127 passed.
- 2026-07-01: Project Review #2 cleanup: removed connector token body fallback; sync endpoints now accept connector token via `X-Connector-Token` header only; backend `pytest -q` => 127 passed.
- 2026-07-01: Project Review #2 follow-up: added event-bus async consumer worker baseline (`worker_async` mode + timeout control + tests), backend `pytest -q` => 128 passed.
- 2026-07-01: Event-bus worker reliability update: added async worker retry policy (`ALLINO_EVENT_BUS_ASYNC_MAX_ATTEMPTS`) + worker diagnostics (`worker_attempts`, `queue_depth`) + fallback-on-exhaustion path; backend `pytest -q` => 130 passed.
- 2026-07-01: Event-bus external worker baseline: added separate worker entrypoint (`python -m app.workers.event_bus_worker`) with Redis request/result contract and shared ingestion processor extraction; backend `pytest -q` => 132 passed.
- 2026-07-01: Event-bus external worker hardening: added retry/backoff + DLQ, worker healthcheck mode, and release-gate strict validation flag (`-RequireExternalWorker`); backend `pytest -q` => 138 passed.
- 2026-07-01: Added dedicated external-worker DLQ smoke path (`staging_smoke_external_worker_dlq.py`) and strict gate flag (`-RequireExternalWorkerDlq`) with report integration; backend `pytest -q` => 140 passed.
