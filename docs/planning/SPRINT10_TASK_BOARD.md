# ALLinO Sprint 10 Task Board

Статус: Closed (S10-01, S10-02 done)
Дата старта: 2026-07-01
Длительность: не оценивается по дням — задачи закрываются по одной, с тестами и обновлением CURRENT_STATE.md.

## Цель спринта

`CLAUDE.md` §5 фиксирует решение от 2026-06-30 ("Extensible Connector Architecture") — Generic HTTP
Connector и Webhook Receiver, чтобы новый источник добавлялся регистрацией конфигурации, а не написанием
Python-кода. Решение было задокументировано, но никогда не реализовано ни на одном спринт-борде.
Пользователь явно выбрал эту задачу как приоритет для Sprint 10 после обзора текущего состояния проекта.

## Правила работы

1. Каждая задача закрывается с тестами + записью в CURRENT_STATE.md.
2. Деструктивные действия — только после явного подтверждения пользователя.
3. Secrets (auth token, webhook secret) никогда не хранятся в БД — только через env/Vault
   (`core/secrets.py`), по имени, детерминированно выводимому из slug коннектора — согласовано с
   security-first baseline (`CLAUDE.md` §4) и существующим паттерном (`ALLINO_SLACK_BOT_TOKEN` и т.п.).

---

## Board (состояния)

### In Progress

- [ ] (нет)

### Done

- [x] S10-01 Generic HTTP Connector (configurable REST poller)
- [x] S10-02 Webhook Receiver (`POST /webhooks/{connector_id}`) with per-connector HMAC verification

---

## S10-01 — Generic HTTP Connector

Why: единственный способ добавить источник сейчас — написать новый `*Connector` класс на Python. Это
прямо противоречит архитектурному решению из `CLAUDE.md` §5.

DoD:

- Новая таблица `generic_connector_configs` (миграция `0010_generic_connectors.sql`): id (UUID, он же
  webhook connector_id), tenant_id, name, slug, base_url, auth_method (none/api_key/bearer/basic),
  auth_header_name, poll_interval_seconds, field_mapping (JSON: externalId/timestamp/preview paths),
  webhook_enabled, status, created_at/updated_at. Без колонок под сами секреты.
- `GenericHttpConnector(BaseConnector)` — реализует контракт `start/stop/health/fetch_events`, как и
  остальные 9 коннекторов; переиспользует `RetryPolicy`/`run_with_retry`.
- Field mapping: dot-path извлечение (`"data.id"`) без индексов массивов — MVP.
- Секрет авторизации резолвится по паттерну `ALLINO_GENERIC_{SLUG}_TOKEN` через `core/secrets.py`
  (env → Vault), как у остальных коннекторов.
- API: `POST/GET /api/v1/ingestion/connectors/generic` (создание/список), `POST
  /api/v1/ingestion/connectors/generic/{id}/sync` (ручной запуск), `DELETE
  .../generic/{id}` — все tenant-scoped, под существующими permission-зависимостями
  (`require_connector_sync_permission` / `require_ingestion_read_permission`).
- Sync-путь переиспользует существующий `_run_connector_sync`-паттерн (event bus, connectors/connector_runs
  телеметрия, аудит) — не параллельная реализация.
- Тесты: извлечение по path, маппинг в UnifiedEvent-словарь, fetch/health lifecycle, CRUD API,
  tenant isolation.

---

## S10-02 — Webhook Receiver

Why: вторая половина решения из `CLAUDE.md` §5 — внешний сервис пушит события напрямую, без поллинга.

DoD:

- `POST /webhooks/{connector_id}` — отдельный роутер, БЕЗ `require_api_key` (внешний вызывающий не знает
  про нашу авторизацию); идентичность и права определяются самой конфигурацией коннектора + HMAC.
- HMAC: заголовок `X-Webhook-Signature: sha256=<hex>` над сырым телом запроса, секрет резолвится по
  паттерну `ALLINO_GENERIC_{SLUG}_WEBHOOK_SECRET`. Fail-closed: `webhook_enabled=true`, но секрет не
  настроен → `503`. Подпись отсутствует/неверна → `401`. Конфиг не найден или webhook не включён → `404`
  (единообразно, чтобы не давать enumeration-сигнал).
- Тело: одиночный JSON-объект или массив (или `{"items"/"data"/"results": [...]}` — тот же конверт, что
  и у poll-пути) — переиспользуется общий парсер конверта.
- Обработка события переиспользует `process_connector_events` + `process_connector_batch` (тот же dedup,
  normalize, audit, event-bus путь, что и у остальных коннекторов) — не параллельный код путь.
- Rate limiting: `/webhooks` добавлен в `core/rate_limit.is_rate_limited_path`.
- Тесты: валидная подпись → приём, невалидная/отсутствующая → 401, не настроенный секрет → 503,
  несуществующий/выключенный webhook → 404, dedup между webhook-доставкой и poll-синком одного и того же
  external_id.

---

## Sprint 10 Exit Criteria

1. S10-01 и S10-02 закрыты с тестами и записью в CURRENT_STATE.md — done.
2. Полный backend test suite зелёный (179 passed), `ruff check app tests --select F,E9` чист,
   `pip-audit -r backend/requirements.txt` чист.
3. `backend/.env.example` документирует паттерн `ALLINO_GENERIC_{SLUG}_TOKEN` /
   `ALLINO_GENERIC_{SLUG}_WEBHOOK_SECRET` (slug в SCREAMING_SNAKE, дефисы → подчёркивания, т.к. POSIX
   env var не допускает дефис) — done.
4. Frontend UI для управления generic-коннекторами — явно вне scope этого спринта (CLAUDE.md §5:
   "via UI or API" — API достаточно для MVP); при необходимости — отдельная задача.
5. `poll_interval_seconds` в конфиге — метаданные для будущего внешнего планировщика/cron, не
   встроенный scheduler: у проекта и так нет внутреннего auto-poll ни для одного из 9 существующих
   коннекторов — синхронизация везде on-demand через `/sync` эндпоинт. Не regression, тот же паттерн.
