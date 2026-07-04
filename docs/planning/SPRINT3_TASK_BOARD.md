# ALLinO Sprint 3 Task Board

Статус: Ready to execute
Дата старта: 2026-07-01
Длительность: 5 рабочих дней (или 10 при part-time)

## Цель спринта

Перейти от закрытого W1/W2 baseline к production-ready read-path: закрыть оставшиеся Wave 1 Core интеграции, усилить ingestion architecture и сформировать release hardening пакет.

## Правила работы

1. Security Gate не должен деградировать относительно текущего состояния.
2. Все новые источники обязаны маппиться в Unified Event Schema без source-specific исключений.
3. Любая архитектурная доработка сопровождается smoke evidence и обновлением CURRENT_STATE.md.

---

## Board (состояния)

### Ready

- [x] S3-01 Реализовать Jira connector (ingest + normalize + persist + tests).
- [x] S3-02 Реализовать Telegram connector (ingest + normalize + persist + tests).
- [x] S3-03 Добавить connector capability matrix endpoint (`/connectors/capabilities`) для UI.
- [x] S3-04 Вынести sync path на event-bus start path (Redis Streams baseline, feature-flagged).
- [x] S3-05 Добавить inbox incremental polling cursor API (opaque cursor, не integer slice).
- [x] S3-06 Расширить frontend operations UX: dedicated panel actions (source filter + run details drawer).
- [x] S3-07 Hardening CI: backend + frontend quality gates (lint scope, test matrix, artifact retention).
- [x] S3-08 Add release hardening checklist execution (security + data + deploy smoke).

### In Progress

- [ ] (нет активных задач)

### Done

- [x] S3-01 Jira connector (ingest + normalize + persist + tests).
- [x] S3-02 Telegram connector (ingest + normalize + persist + tests).
- [x] S3-03 connector capability matrix endpoint + UI dynamic sources.
- [x] S3-04 feature-flagged Redis Streams start path.
- [x] S3-05 opaque cursor inbox pagination API.
- [x] S3-06 frontend operations UX filters + run details.
- [x] S3-07 CI hardening (matrix + artifacts + stricter lint scope).
- [x] S3-08 release hardening checklist snapshot.

### Blocked

- [ ] (блокеры и зависимости)

---

## Детализация задач (DoD)

### S3-01 Jira connector

Состав:

- Jira API client (cloud-first), минимальные scopes
- mapping Jira issue/activity -> Unified Event
- sync endpoint + audit + connector registry/runs integration

DoD:

- минимум 10 seeded/fixture events проходят ingest -> inbox
- auth/rate-limit ошибки обрабатываются корректно
- тесты: mapping + sync endpoint + security policy paths

### S3-02 Telegram connector

Состав:

- Telegram ingest adapter (bot/update based)
- mapping message/update -> Unified Event
- sync endpoint + audit + connector registry/runs integration

DoD:

- минимум 10 fixture updates проходят ingest -> inbox
- tenant isolation и idempotency подтверждены тестами

### S3-03 Capabilities endpoint

Состав:

- backend endpoint с публичным списком доступных connectors/features
- source-level flags: available, configured, requires_secret, sync_supported

DoD:

- frontend может рендерить availability без hardcoded source list
- endpoint tenant-scoped и защищен read permission policy

### S3-04 Redis Streams start path

Состав:

- feature flag: `ALLINO_EVENT_BUS_ENABLED`
- publish step из sync/ingestion path
- consumer worker baseline (local mode)

DoD:

- при включенном флаге ingest path использует stream publish + consume
- retries/back-pressure path демонстрируются в smoke evidence

### S3-05 Opaque cursor API

Состав:

- `GET /inbox` курсорная пагинация (opaque token)
- обратная совместимость с limit

DoD:

- курсор не зависит от integer index в коннекторах
- API покрыт тестами happy/error paths

### S3-06 Frontend operations UX extension

Состав:

- filters на operations panel (source/status)
- run details drawer with error metadata + counters
- preserved existing token-driven design language

DoD:

- пользователь может быстро диагностировать сбой source без перехода в logs
- build/typecheck проходят

### S3-07 CI hardening

Состав:

- расширенный lint coverage
- тест matrix (backend/frontend)
- устойчивые caching/artifacts настройки

DoD:

- CI выявляет regressions раньше merge
- нет ложноположительных падений на стандартном пути

### S3-08 Release hardening checklist

Состав:

- security checklist pass
- migration safety pass
- staging smoke pass

DoD:

- итоговый go/no-go checklist зафиксирован в planning docs

---

## Рекомендованный порядок выполнения

### Day 1

- S3-01 (Jira connector scaffold + mapping tests)
- S3-03 (capabilities endpoint contract)

### Day 2

- S3-01 (sync endpoint finish)
- S3-02 (Telegram scaffold)

### Day 3

- S3-02 (sync endpoint finish)
- S3-05 (cursor API design + implementation)

### Day 4

- S3-04 (Redis Streams feature-flag path)
- S3-06 (frontend operations UX extension)

### Day 5

- S3-07 (CI hardening)
- S3-08 (release checklist + final smoke)

---

## Sprint 3 Exit Criteria

1. Оставшиеся Wave 1 Core источники (Jira, Telegram) доступны в MVP read-path.
2. Ingestion architecture поддерживает event-bus start path (feature-flagged Redis Streams).
3. UI показывает connector operations статус и историю без hardcoded source assumptions.
4. Cursor pagination готова для production-like polling.
5. CI + release hardening checklist закрыты и задокументированы.

---

## Журнал решений

- 2026-07-01: Sprint 3 board создан после фактического закрытия W1/W2 и post-W2 hardening блока.
- 2026-07-01: S3-01 закрыт. Добавлен Jira connector (`jira_connector.py`), endpoint `/api/v1/ingestion/connectors/jira/sync`, тесты `test_jira_connector.py` и `test_jira_sync_endpoint.py`. Backend suite: 69 passed.
- 2026-07-01: S3-02 закрыт. Добавлен Telegram connector (`telegram_connector.py`), endpoint `/api/v1/ingestion/connectors/telegram/sync`, тесты `test_telegram_connector.py` и `test_telegram_sync_endpoint.py`. Backend suite: 72 passed.
- 2026-07-01: S3-03 закрыт. Добавлен endpoint `/api/v1/ingestion/connectors/capabilities` и тест `test_connector_capabilities_endpoint.py`; Sidebar переведен на dynamic sources из capabilities API (без hardcoded списка). Backend suite: 73 passed.
- 2026-07-01: S3-04 закрыт. Добавлен feature-flagged event-bus path (`services/event_bus.py`) с режимами `direct` / `redis_stream` / `redis_fallback`; sync pipeline использует event bus processing; добавлены тесты `test_event_bus.py` и `test_event_bus_sync_response.py`. Backend suite: 76 passed.
- 2026-07-01: S3-05 закрыт. Добавлен opaque cursor API для inbox (`/api/v1/ingestion/inbox/page`) и cursor support в `/api/v1/ingestion/inbox`; добавлен тест `test_inbox_cursor_api.py`. Backend suite: 78 passed.
- 2026-07-01: S3-06 закрыт. `ConnectorOpsPanel` расширен source/status фильтрами и run details block (выбор запуска из списка). Frontend build проходит.
- 2026-07-01: S3-07 закрыт. CI workflows усилены: backend Python matrix (3.12/3.13), frontend Node matrix (20/22), artifact retention (test/build logs), lint scope `F,E9`.
- 2026-07-01: S3-08 закрыт. Добавлен `docs/planning/RELEASE_HARDENING_CHECKLIST_S3.md` с execution snapshot и текущим GO-статусом для продолжения sprint baseline.
