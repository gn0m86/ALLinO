# ALLinO Sprint 4 Task Board

Статус: Ready to execute
Дата старта: 2026-07-01
Длительность: 5 рабочих дней (или 10 при part-time)

## Цель спринта

Расширить Wave 1 Optional интеграции и стабилизировать production-readiness paths после полного закрытия Sprint 3.

## Правила работы

1. Security baseline из Sprint 3 не деградирует.
2. Новые интеграции подключаются только через официальный API.
3. Любая новая функциональность сопровождается тестами и обновлением planning-доков.

---

## Board (состояния)

### Ready

- [x] S4-01 Реализовать Slack connector (own workspace) end-to-end.
- [x] S4-02 Добавить smoke сценарий event-bus режима с Redis в runbook.
- [x] S4-03 Добавить inbox incremental polling на frontend через `/inbox/page`.
- [x] S4-04 Улучшить capabilities endpoint (configured/requires_secret из env/runtime).
- [x] S4-05 Добавить Sprint 4 release checklist snapshot.

### In Progress

- [ ] (нет активных задач)

### Done

- [x] S4-01 Slack connector (own workspace) end-to-end.
- [x] S4-02 Redis event-bus smoke scenario in runbook.
- [x] S4-03 Frontend inbox cursor-based polling via `/inbox/page`.
- [x] S4-04 runtime-aware connector capabilities flags.
- [x] S4-05 release hardening checklist snapshot.

### Blocked

- [ ] (блокеры и зависимости)

---

## Sprint 4 Exit Criteria

1. Slack подключен как Wave 1 Optional интеграция с тестовым покрытием.
2. Frontend использует cursor-based polling path.
3. Event-bus smoke шаги документированы и воспроизводимы.
4. Runtime capability flags отражают фактическую конфигурацию.
5. Checklist и handoff синхронизированы.

---

## Журнал решений

- 2026-07-01: Sprint 4 board создан после полного закрытия Sprint 3.
- 2026-07-01: S4-01 закрыт. Добавлен Slack connector (`slack_connector.py`), endpoint `/api/v1/ingestion/connectors/slack/sync`, тесты `test_slack_connector.py` и `test_slack_sync_endpoint.py`; capabilities и UI source-style обновлены. Backend suite: 81 passed.
- 2026-07-01: S4-02 закрыт. `SMOKE_RUNBOOK.md` дополнен Redis event-bus smoke сценарием с expected outcomes (`redis_stream` / `redis_fallback`).
- 2026-07-01: S4-03 закрыт. Frontend inbox загрузка переведена на `/api/v1/ingestion/inbox/page` с cursor-based polling и dedup merge.
- 2026-07-01: S4-04 закрыт. `connectors/capabilities` переведен на runtime env-driven `configured` flags и `requires_secret`; тесты обновлены.
- 2026-07-01: S4-05 закрыт. Добавлен `docs/planning/RELEASE_HARDENING_CHECKLIST_S4.md` с execution snapshot и GO оценкой.
