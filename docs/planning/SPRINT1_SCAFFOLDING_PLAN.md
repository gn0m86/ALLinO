# ALLinO Sprint 1 Scaffolding Plan

Статус: Ready
Цель: быстро поднять минимальный каркас проекта под задачи Sprint 1 без лишней сложности.

## 1. Порядок создания (обязательно в этой последовательности)

1. Backend skeleton
2. Shared contracts
3. DB migrations + RLS baseline
4. Ingestion/normalization path
5. Frontend shell
6. CI baseline

## 2. Целевая структура файлов

```text
e:/My_prjts/ALLinO/
  backend/
    app/
      main.py
      api/
        health.py
        ingestion.py
      core/
        config.py
        security.py
        tenant.py
      domain/
        models.py
        events.py
      connectors/
        base.py
        mock_connector.py
      services/
        normalizer.py
        dedup.py
        audit.py
      db/
        session.py
        repositories/
          messages_repo.py
          threads_repo.py
          audit_repo.py
    migrations/
      0001_init.sql
      0002_rls.sql
    tests/
      test_schema_validation.py
      test_tenant_isolation.py
      test_ingestion_idempotency.py
  frontend/
    src/
      app/
        layout.tsx
        page.tsx
      components/
        Sidebar.tsx
        InboxList.tsx
        ThreadPanel.tsx
        ModeToggle.tsx
      lib/
        api.ts
        types.ts
  shared/
    contracts/
      unified_event.schema.json
      examples/
        valid_event.json
        invalid_event_missing_field.json
  docs/
    planning/
      SPRINT1_SCAFFOLDING_PLAN.md
```

## 3. Минимальные контракты на старте

### 3.1 Unified Event Contract

Файл: shared/contracts/unified_event.schema.json

Обязательные поля v1:

- eventId
- tenantId
- sourceType
- externalId
- timestamp
- payload
- schemaVersion

### 3.2 Connector Base Contract

Файл: backend/app/connectors/base.py

Минимальный интерфейс:

- start()
- stop()
- health()
- fetch_events(cursor)

### 3.3 Ingestion API Contract

Файл: backend/app/api/ingestion.py

Endpoints:

- POST /api/v1/ingestion/events
- GET /api/v1/ingestion/health

Поведение:

- невалидные события -> 400
- дубликаты -> 200 idempotent
- валидные события -> publish/normalize/persist

## 4. БД и RLS baseline

Файлы:

- backend/migrations/0001_init.sql
- backend/migrations/0002_rls.sql

Таблицы минимум:

- users
- connectors
- threads
- messages
- audit_logs

Правило:

- каждая таблица с tenant_id
- RLS policy: доступ только для текущего tenant

## 5. Definition of Done для scaffolding

1. backend стартует локально
2. frontend shell рендерится локально
3. ingestion endpoint принимает валидный mock event
4. normalizer сохраняет событие в messages/threads
5. tenant isolation тест проходит
6. CI прогоняет lint + tests + build

## 6. Что не делать в Sprint 1 scaffolding

- не внедрять сложный plugin runtime
- не строить полноценный write-back
- не добавлять production-grade orchestration
- не расширять schema beyond v1 без необходимости

## 7. Быстрый старт задач по дням

Day 1:

- backend/app/main.py
- shared/contracts/unified_event.schema.json
- frontend shell files

Day 2:

- migrations 0001/0002
- ingestion.py
- normalizer.py

Day 3:

- repositories
- dedup.py
- тесты schema/idempotency

Day 4:

- audit path
- tenant isolation tests
- UI reads from test data

Day 5:

- CI hardening
- smoke check
- обновление документации запуска
