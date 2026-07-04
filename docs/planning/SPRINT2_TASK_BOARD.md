# ALLinO Sprint 2 Task Board

Статус: Closed (выполнено)
Дата старта: после закрытия Sprint 1 Exit Criteria
Длительность: 5 рабочих дней (или 10 при part-time)

## Цель спринта

Дать рабочий vertical slice MVP с первыми Core-интеграциями, приоритизацией и устойчивыми UX error states.

## Правила работы

1. Не ломаем Security Gate из PREBUILD_SPEC_V1.md.
2. Все коннекторы отдают события строго в Unified Event Schema.
3. Любой UX state в ошибках должен быть наблюдаем и воспроизводим в тестах.

---

## Board (состояния)

### Ready

- [x] S2-01 Выбрать первые 3 коннектора из Wave 1 Core для реализации.
- [x] S2-02 Реализовать коннектор #1 (ingest + normalize + persist + smoke test).
- [x] S2-03 Реализовать коннектор #2 (ingest + normalize + persist + smoke test).
- [x] S2-04 Реализовать коннектор #3 (ingest + normalize + persist + smoke test).
- [x] S2-05 Внедрить dedup strategy (hash + idempotency guard).
- [x] S2-06 Реализовать rule-based priority classifier v1.
- [x] S2-07 Реализовать thread context linking v1.
- [x] S2-08 Реализовать inbox filters (unread/source/priority).
- [x] S2-09 Реализовать UX error/empty states (connect source, sync interruption, rate limit).
- [x] S2-10 Добавить observability минимум (ingestion lag, error rate, retry counts).

### In Progress

(none)

### Done

- [x] S2-01 Выбрать первые 3 коннектора из Wave 1 Core для реализации.
- [x] S2-02 Реализовать коннектор #1 (ingest + normalize + persist + smoke test).
- [x] S2-03 Реализовать коннектор #2 (ingest + normalize + persist + smoke test).
- [x] S2-04 Реализовать коннектор #3 (ingest + normalize + persist + smoke test).
- [x] S2-05 Внедрить dedup strategy (hash + idempotency guard).
- [x] S2-06 Реализовать rule-based priority classifier v1.
- [x] S2-07 Реализовать thread context linking v1.
- [x] S2-08 Реализовать inbox filters (unread/source/priority).
- [x] S2-09 Реализовать UX error/empty states (connect source, sync interruption, rate limit).
- [x] S2-10 Добавить observability минимум (ingestion lag, error rate, retry counts).

### Blocked

- [ ] (блокеры и зависимости)

---

## Детализация задач (DoD)

### S2-01 Выбор 3 коннекторов

Критерии выбора:

- ценность для dev workflow,
- стабильность API,
- минимальный security риск.

Рекомендация по умолчанию:

- GitHub,
- GitLab,
- Jira или Linear.

DoD:

- Зафиксирован shortlist с аргументацией в decision log.

### S2-02..S2-04 Коннекторы

Состав для каждого:

- auth flow (минимальные scopes),
- ingest path,
- normalize to schema,
- persist,
- статус синхронизации в UI.

DoD для каждого:

- минимум 10 тестовых событий корректно отображаются в inbox.
- ошибки auth/rate-limit корректно отображаются пользователю.
- логируются audit-события подключения и синхронизации.

### S2-05 Dedup strategy

Состав:

- dedup hash generation,
- idempotency checks,
- safe retries.

DoD:

- повторная доставка не создает дубли в UI и БД.

### S2-06 Priority classifier v1

Состав:

- правила по source + event type + keywords,
- приоритеты low/normal/high,
- конфиг по умолчанию.

DoD:

- приоритет выставляется консистентно и объяснимо.
- есть тесты на базовые rule paths.

### S2-07 Thread context linking

Состав:

- связывание по external ids,
- fallback-эвристики,
- отображение связанного контекста в thread panel.

DoD:

- связанные события корректно группируются в треды.

### S2-08 Inbox filters

Состав:

- unread filter,
- source filter,
- priority filter,
- корректная комбинация фильтров.

DoD:

- фильтры работают совместно, состояние фильтров сохраняется в сессии.

### S2-09 UX error/empty states

Состав:

- connect source fail,
- sync interruption,
- rate limit wait,
- empty inbox after onboarding.

DoD:

- пользователь всегда видит следующий осмысленный шаг.
- нет тупиковых экранов.

### S2-10 Observability minimum

Состав:

- ingestion lag,
- retry count,
- normalized vs rejected events,
- connector health status.

DoD:

- метрики доступны для sprint review и диагностики.

---

## День-за-днем (рекомендованный ритм)

### Day 1

- S2-01
- S2-02 (начало)
- S2-05 (каркас)

### Day 2

- S2-02 (финал)
- S2-03 (начало)
- S2-06 (каркас)

### Day 3

- S2-03 (финал)
- S2-04 (начало)
- S2-07 (каркас)

### Day 4

- S2-04 (финал)
- S2-08
- S2-09

### Day 5

- S2-10
- Интеграционный smoke прогон
- Sprint review + решение по следующим 2 коннекторам Wave 1

---

## Sprint 2 Exit Criteria

1. Минимум 3 Core-интеграции стабильно ingest события.
2. В inbox корректно работают приоритеты и фильтры.
3. Thread linking показывает полезный контекст.
4. Error/empty states покрывают ключевые сбои.
5. Security Gate не деградирован относительно Sprint 1.

---

## Быстрый журнал решений

- Decision log (добавлять по мере работы):
- 2026-06-25: S2-01 закрыт. Shortlist коннекторов для Sprint 2: GitHub, GitLab, Linear.
- 2026-06-25: Старт S2-02. Добавлен `GitHubConnector` scaffold с mapping GitHub notifications -> Unified Event и тесты `tests/test_github_connector.py`.
- 2026-06-25: S2-02 закрыт. Добавлен endpoint `/api/v1/ingestion/connectors/github/sync` с persist+audit path, тест `tests/test_github_sync_endpoint.py`, runtime smoke: processed=3, inserted=3, rejected=0.
- 2026-06-25: S2-03 закрыт. Добавлен endpoint `/api/v1/ingestion/connectors/gitlab/sync` с persist+audit path, тесты `tests/test_gitlab_connector.py` и `tests/test_gitlab_sync_endpoint.py`, runtime smoke: processed=3, inserted=3, rejected=0.
- 2026-06-25: S2-04 закрыт. Добавлен endpoint `/api/v1/ingestion/connectors/linear/sync` с persist+audit path, тесты `tests/test_linear_connector.py` и `tests/test_linear_sync_endpoint.py`, runtime smoke: processed=3, inserted=3, rejected=0.
- 2026-06-30: Security hardening (вне нумерации S2, но блокировало S2 exit criteria #5). Закрыты P0 уязвимости из PROJECT_REVIEW.md: API key middleware, resolve_tenant_id на /events+/validate+/seed, tenant mismatch guard, limit clamp, extra="forbid", CORS сужен, lifespan, migration tracking, audit index. Все 11 тестов проходят.
- 2026-06-30: Design system интегрирован. docs/design_handoff_secure_inbox/ подключён; токены живые в globals.css; frontend переписан под Quiet Slate spec (3-pane layout, Sidebar, InboxList, ThreadPanel, Icons). CLAUDE.md § 6 обновлён правилами для UI-работы.
- 2026-06-30: S2-10 закрыт. `services/metrics.py` — in-memory MetricsStore (thread-safe); `base.py` — `last_retry_count` tracking в `run_with_retry`; все 3 коннектора пишут `retry_count` в health.details; `_process_connector_batch` вычисляет ingestion lag; `GET /api/v1/ingestion/metrics` эндпоинт. 5 тестов в `test_metrics.py`. Итого: 33/33 тестов.
- 2026-07-01: S2-05..09 верифицированы по коду и закрыты в task board. Sprint 2 закрыт полностью. Все exit criteria выполнены.
- 2026-07-01: W1-08 закрыт. `docker-compose.yml` обновлён: ALLINO*API_KEY env var, NEXT_PUBLIC*\* как build args, healthcheck на backend. `frontend/Dockerfile` принимает ARG для NEXT_PUBLIC vars. `.dockerignore` для backend и frontend. `frontend/package.json` + `typecheck` script. `.github/workflows/frontend-ci.yml` (typecheck + next build). `domain/models.py` подтверждён отсутствующим.

## Риски спринта

1. Риск: перегрузка команды интеграциями.

- Контроль: жесткий лимит 3 коннектора в спринт.

2. Риск: нестабильность webhook/polling потоков.

- Контроль: retry policy + idempotency + status visibility.

3. Риск: UX деградация при ошибках.

- Контроль: обязательное тестирование error paths до demo.
