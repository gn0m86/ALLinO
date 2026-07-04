# ALLinO Sprint Plan (W1-W2)

Статус: Ready
Дата: 2026-06-25
Горизонт: 2 спринта по 1 неделе (или 2x2 недели при меньшей команде)

## Командные принципы

- Security checks включены в каждую user story.
- Любой коннектор реализуется через unified event contract.
- No merge без DoD и минимальных тестов.

Связанный документ исполнения Sprint 1:

- [SPRINT1_TASK_BOARD.md](SPRINT1_TASK_BOARD.md)

Связанный документ исполнения Sprint 2:

- [SPRINT2_TASK_BOARD.md](SPRINT2_TASK_BOARD.md)

Стартовый чеклист перед реализацией:

- [IMPLEMENTATION_KICKOFF_CHECKLIST.md](IMPLEMENTATION_KICKOFF_CHECKLIST.md)

Scaffolding план Sprint 1:

- [SPRINT1_SCAFFOLDING_PLAN.md](SPRINT1_SCAFFOLDING_PLAN.md)

Файл правил для ИИ-агентов (repo root):

- [../../CLAUDE.md](../../CLAUDE.md)

Быстрый запуск и smoke проверка:

- [DEV_QUICKSTART.md](DEV_QUICKSTART.md)
- [SMOKE_RUNBOOK.md](SMOKE_RUNBOOK.md)

---

## Sprint 1: Foundation and Security Skeleton

Цель: запустить безопасный каркас ingestion -> normalization -> inbox read path.

### Deliverables

1. Repository structure и базовая app shell.
2. Unified Event Schema v1 (валидатор + примеры событий).
3. Connector framework (интерфейс адаптера + lifecycle + retry policy).
4. Базовый ingestion pipeline:

- raw event -> normalization -> persisted message metadata.

5. Security skeleton:

- auth foundation,
- tenant context propagation,
- secrets integration (Vault interface/stub),
- audit append flow.

6. UI shell:

- Sidebar,
- Inbox list stub,
- Thread panel stub,
- базовые режимы Focus/Incident как toggles состояния.

### Stories (W1)

- W1-S1: Определить контракты доменной модели (event, thread, connector).
- W1-S2: Реализовать schema validation для unified events.
- W1-S3: Поднять storage schema с tenant_id и RLS-политиками.
- W1-S4: Реализовать ingestion endpoint + queue publish/consume.
- W1-S5: Реализовать audit trail append-only path.
- W1-S6: Реализовать UI shell и чтение тестовых событий из БД.

### Definition of Done (W1)

- Все события проходят schema validation.
- Tenant A не видит данные Tenant B (автотест/интеграционный тест).
- Есть рабочий read path от ingestion до inbox list.
- Audit события записываются append-only.
- CI проходит lint/test/build без критичных security warning.

---

## Sprint 2: Wave 1 Core Integrations and Usable MVP Slice

Цель: дать рабочий vertical slice для первых интеграций и приоритизации.

### Deliverables

1. Коннекторы Core Wave 1 (минимум 3 из 5): GitHub, GitLab, Jira, Linear, Telegram.
2. Rule-based priority classifier v1.
3. Thread context linking v1.
4. Inbox filters:

- unread,
- source,
- priority.

5. Error/empty states для:

- connect source,
- sync interruption,
- rate limit.

6. Security visibility в UI:

- источник,
- статус синхронизации,
- базовый security badge.

### Stories (W2)

- W2-S1: Реализовать 3 приоритетных адаптера по единому интерфейсу.
- W2-S2: Внедрить dedup strategy (hash + idempotency guard).
- W2-S3: Реализовать priority rules engine (конфигурируемый).
- W2-S4: Реализовать thread stitching (external ids + heuristics).
- W2-S5: Реализовать UX состояния ошибок и пустых сценариев.
- W2-S6: Добавить базовые observability метрики по ingestion и sync.

### Definition of Done (W2)

- Минимум 3 core source интеграции стабильно ingest события.
- Пользователь видит события в unified inbox с правильной приоритизацией.
- Ошибки подключения и rate limit отображаются корректно и не ломают сессию.
- Security gate P0 элементы не деградированы.
- Документация setup/usage обновлена.

---

## Prioritized Backlog After W2

1. Довести все 5 Wave 1 Core интеграций.
2. Добавить Slack и Google Calendar/Meet как optional path.
3. Улучшить фильтры, snooze/defer, пользовательские правила.
4. Подготовить release hardening checklist.

---

## Risks and Mitigation

1. Риск: нестабильность API лимитов у провайдеров.

- Mitigation: backoff + retry + queue buffering + explicit sync status.

2. Риск: расползание scope в write-back.

- Mitigation: strict read-first boundary в рамках v1.

3. Риск: рост сложности архитектуры раньше времени.

- Mitigation: delivery-first vertical slices, без premature scaling.

4. Риск: UX отстанет от backend.

- Mitigation: UI shell и error states строятся параллельно с ingestion.
