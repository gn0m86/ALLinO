# ALLinO Sprint 5 Task Board

Статус: Completed
Дата старта: 2026-07-01
Длительность: 5 рабочих дней (или 10 при part-time)

## Цель спринта

Начать Wave 2 интеграции и укрепить runtime readiness после полного закрытия Sprint 4.

## Правила работы

1. Security-first baseline из Sprint 4 сохраняется без ослаблений.
2. Новые интеграции — только официальные API и минимальные scopes.
3. Любая задача закрывается с тестами и актуализацией planning docs.

---

## Board (состояния)

### Ready

- [x] S5-01 Реализовать Discord connector end-to-end.
- [x] S5-02 Добавить capability flags для Wave 2 источников (Discord/Zoom/Teams) с runtime configured status.
- [x] S5-03 Добавить frontend indicator для connectors `configured=false` в Sources панели.
- [x] S5-04 Расширить smoke runbook сценариями для Slack/Discord sync.
- [x] S5-05 Добавить Sprint 5 release checklist snapshot.

### In Progress

- [ ] (нет активных задач)

### Done

- [x] S5-01 Discord connector end-to-end.
- [x] S5-02 Wave 2 capability flags (Discord/Zoom/Teams).
- [x] S5-03 Frontend configured=false indicator in Sources.
- [x] S5-04 Smoke runbook expanded for Slack/Discord sync.
- [x] S5-05 Sprint 5 release hardening checklist snapshot.

### Blocked

- [ ] (блокеры и зависимости)

---

## Sprint 5 Exit Criteria

1. Discord доступен в read-path с тестовым покрытием.
2. Capability matrix отражает Wave 2 runtime readiness.
3. UI показывает конфигурационный статус источников.
4. Smoke runbook покрывает новые sync сценарии.
5. Sprint 5 checklist и handoff синхронизированы.

---

## Журнал решений

- 2026-07-01: Sprint 5 board создан после закрытия Sprint 4.
- 2026-07-01: S5-01 закрыт. Добавлен Discord connector (`discord_connector.py`), endpoint `/api/v1/ingestion/connectors/discord/sync`, тесты `test_discord_connector.py` и `test_discord_sync_endpoint.py`; capabilities и UI source-style обновлены. Backend suite: 85 passed.
- 2026-07-01: S5-02/S5-03 закрыты. Capabilities matrix расширена `zoom`/`teams` (runtime configured flags), в Sources добавлен setup-indicator для `configured=false`.
- 2026-07-01: S5-04/S5-05 закрыты. Smoke runbook дополнен Slack/Discord sync сценариями; добавлен release snapshot `RELEASE_HARDENING_CHECKLIST_S5.md`.
- 2026-07-01: Финальная валидация после всех правок Sprint 5: backend `pytest -q` => 85 passed; frontend `npm --prefix frontend run build` => success.
