# ALLinO Sprint 1 Task Board

Статус: Execution complete (scope-based)
Дата старта: TBD
Длительность: 5 рабочих дней (или 10 при part-time)

## Цель спринта

Запустить безопасный каркас пути raw event -> normalization -> storage -> inbox read path.

## Правила работы

1. Любая задача закрывается только с проверкой security impact.
2. Нет merge без теста или явного TODO с датой закрытия.
3. Любые изменения схемы данных сопровождаются миграцией.

---

## Board (состояния)

### Ready

- [x] S1-01 Создать структуру репозитория и модулей backend/frontend.
- [x] S1-02 Описать Unified Event Schema v1 и добавить JSON schema validator.
- [x] S1-03 Реализовать интерфейс коннектора (adapter contract).
- [x] S1-04 Поднять базовую схему БД с tenant_id и RLS policy.
- [x] S1-05 Реализовать ingestion endpoint (прием raw events).
- [x] S1-06 Реализовать normalizer service (валидация + маппинг).
- [x] S1-07 Реализовать запись в messages/threads (read path минимум).
- [x] S1-08 Реализовать append-only audit path.
- [x] S1-09 Сделать UI shell: Sidebar + Inbox list stub + Thread panel stub.
- [x] S1-10 Настроить CI minimum: lint + unit tests + build.

### In Progress

- [ ] (нет активных задач)

### Done

- [x] S1-01 Создать структуру репозитория и модулей backend/frontend.
- [x] S1-02 Описать Unified Event Schema v1 и добавить JSON schema validator.
- [x] S1-03 Реализовать интерфейс коннектора (adapter contract).
- [x] S1-04 Поднять базовую схему БД с tenant_id и RLS policy.
- [x] S1-05 Реализовать ingestion endpoint (прием raw events).
- [x] S1-06 Реализовать normalizer service (валидация + маппинг).
- [x] S1-07 Реализовать запись в messages/threads (read path минимум).
- [x] S1-08 Реализовать append-only audit path.
- [x] S1-09 Сделать UI shell: Sidebar + Inbox list stub + Thread panel stub.
- [x] S1-10 Настроить CI minimum: lint + unit tests + build.

### Blocked

- [ ] (блокеры и зависимости)

---

## Детализация задач (DoD)

### S1-01 Repo skeleton

Состав:

- backend app entry
- frontend app shell
- shared contracts folder
- docs для локального запуска

DoD:

- Единая команда запуска локальной среды.
- Структура директорий соответствует архитектурному baseline.

### S1-02 Unified Event Schema v1

Состав:

- schema file
- примеры valid/invalid payload
- runtime validation в ingestion

DoD:

- Невалидные payload отклоняются с понятной ошибкой.
- Есть автотесты для schema happy/error paths.

### S1-03 Connector adapter contract

Состав:

- интерфейс адаптера
- lifecycle hooks (start, stop, health)
- retry policy contract

DoD:

- Можно подключить mock-коннектор без изменения core кода.

### S1-04 DB + RLS

Состав:

- таблицы users/threads/messages/connectors/audit
- tenant_id в таблицах
- базовые RLS policies

DoD:

- Интеграционный тест подтверждает изоляцию tenant A/B.

### S1-05 Ingestion endpoint

Состав:

- endpoint для raw event
- idempotency key support
- базовые rate limits

DoD:

- endpoint принимает валидное событие и не дублирует одинаковые события.

### S1-06 Normalizer service

Состав:

- маппинг raw -> unified event
- canonical fields
- timestamp normalization UTC

DoD:

- normalized event стабильно формируется для тестовых кейсов.

### S1-07 Persisted read path

Состав:

- запись сообщений и тредов
- выборка inbox списка
- получение thread details

DoD:

- UI видит тестовые сообщения из БД.

### S1-08 Audit append path

Состав:

- логирование security-sensitive операций
- запрет update/delete для audit записи

DoD:

- Попытка модификации audit записи отклоняется.

### S1-09 UI shell

Состав:

- sidebar nav
- inbox list placeholder
- thread panel placeholder
- переключатели Focus/Incident состояния

DoD:

- Базовая навигация работает, состояние не теряется при переключениях.

### S1-10 CI baseline

Состав:

- lint
- unit test
- build check

DoD:

- PR без прохождения CI не может быть смержен.

---

## День-за-днем (рекомендованный ритм)

### Day 1

- S1-01
- S1-02 (черновик)
- S1-10 (каркас CI)

### Day 2

- S1-02 (финал)
- S1-03
- S1-04 (миграции)

### Day 3

- S1-05
- S1-06
- Тесты на валидацию и idempotency

### Day 4

- S1-07
- S1-08
- Интеграционный тест tenant isolation

### Day 5

- S1-09
- Финальный smoke прогон end-to-end
- Sprint review и перенос хвостов

---

## Sprint 1 Exit Criteria

1. Работает путь от ingestion до отображения в inbox list.
2. RLS изоляция подтверждена тестом.
3. Audit path append-only подтвержден проверкой.
4. CI минимальный pipeline стабилен.
5. Документация локального запуска актуальна.

---

## Быстрый журнал решений

- Decision log (добавлять по мере работы):
- 2026-06-25: Выполнен backend smoke runbook end-to-end. Добавлены endpoints `/api/v1/ingestion/validate` и `/api/v1/ingestion/stats`.
- 2026-06-25: Исправлен путь миграций в `backend/app/db/session.py` (`MIGRATIONS_DIR = BASE_DIR / "migrations"`) после runtime ошибки `no such table`.
- 2026-06-25: Закрыт S1-03. Добавлен connector adapter contract (lifecycle + health + retry policy), реализован `MockConnector`, добавлен автотест `tests/test_connector_contract.py`.
- 2026-06-25: Закрыт S1-10. Добавлен workflow `.github/workflows/backend-ci.yml` (lint/test/build-check) и `backend/requirements-dev.txt`; локальный прогон успешен.
- 2026-06-25: Закрыт S1-04 для текущего SQLite scope: tenant-scoped read-path (`inbox`/`audit`/`stats`) + тест `tests/test_tenant_isolation.py` + runtime smoke для tenant A/B. В `0002_rls.sql` сохранен шаблон RLS для Postgres hardening.
- 2026-06-25: Добавлен frontend runtime setup (Next.js packaging + `.env.example`); `npm --prefix frontend run build` и `npm --prefix frontend run dev` проходят успешно.

## Риски спринта

1. Слишком раннее усложнение архитектуры.

- Контроль: фиксируем минимальный vertical slice, без premature scaling.

2. Задержки из-за миграций и RLS.

- Контроль: сначала минимальные таблицы и базовые policies, затем расширение.

3. Разрыв backend и frontend ритма.

- Контроль: UI работает на тестовых данных уже с Day 2-3.
