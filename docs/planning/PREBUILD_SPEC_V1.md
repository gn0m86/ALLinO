# ALLinO Pre-build Spec v1

Статус: Approved for implementation start
Дата: 2026-06-25
Основание: Нормализация v1 + v2 из PROJECT_MASTER_BRIEF.md и каноничные ответы в docs/agent-answers/incoming

## 1. Product Baseline

Продукт: secure, reading-first unified inbox для разработчиков и удаленных команд.

Цель первой версии:

- Собирать входящие из рабочих источников в одном месте.
- Снижать шум через приоритизацию и режимы фокуса.
- Давать прозрачность безопасности и происхождения данных.

Нефункциональный приоритет:

1. Security-first
2. Privacy-first
3. Local-first

## 2. MVP Scope (P0/P1)

### P0

- Подключение источников (Wave 1 Core): GitHub, GitLab, Jira, Linear, Telegram.
- Read-only ingestion и унификация событий.
- Unified Inbox + Thread View.
- Rule-based priority classifier.
- Focus Mode и Incident Mode как состояния оболочки.
- Security visibility (базовые security-индикаторы и audit видимость).
- Базовые empty/error states в ключевых сценариях.

### P1 (если успеваем без риска)

- Slack (свой workspace).
- Google Calendar/Meet (с обязательным авто-renew watch channels).
- Snooze/defer и улучшенные фильтры.

### Out of scope для первого релиза

- Полный write-back по всем источникам.
- Cloud convenience функции как обязательная часть релиза.
- Plugin marketplace и широкая экосистема плагинов.
- Интеграции Wave 2/3 как блокер релиза.

## 3. Security Gate (Must-pass)

Перед релизом обязательно:

- JWT hardening.
- Tenant isolation (tenant_id + RLS).
- Encryption at rest и секреты через Vault.
- CSP/HSTS и базовый transport hardening.
- MFA для admin-потоков.
- Append-only audit logs.
- Rate limits на auth и ingestion endpoints.

Принцип: любое функциональное решение, которое ослабляет Security Gate, не проходит в релиз.

## 4. UX/IA Baseline

- Точка входа: Unified Inbox.
- L1 разделы: Inbox, Focus, Incident, Security Center, Settings.
- Thread View: overlay/panel.
- Focus и Incident: режимы интерфейса, а не отдельные приложения.
- Onboarding: минимум один источник, но без жесткой блокировки пользователя навсегда.

## 5. Technical Baseline

- Модульная архитектура: Connector Layer, Normalization Engine, Encryption Service, Audit Log Service.
- Unified Event Schema как обязательный контракт.
- Event bus: Redis Streams на старте, Kafka как scale-out путь.
- Sync: cursor-based delta sync + offline cache.
- Plugin SDK: направление на WASM, но не блокер v1.

### 5.1 Extensible Connector Architecture (добавлено 2026-06-30)

Цель: любой источник (встроенный или кастомный) должен работать через одну и ту же механику.

**Connector Registry**
- Таблица `connectors` в БД хранит все зарегистрированные коннекторы.
- Поля: `id`, `tenant_id`, `source_type`, `status`, `config` (JSON — auth, URL, field mapping, polling interval).
- Встроенные коннекторы (GitHub, GitLab и т.д.) — это предустановленные профили в реестре, не отдельная кодовая ветка.

**Generic HTTP Connector**
- Универсальный коннектор для любого REST API.
- Конфигурируется через UI/API без написания кода:
  - `base_url` — endpoint для polling
  - `auth_type`: `api_key` | `bearer` | `basic`
  - `auth_config`: заголовок/значение/credentials
  - `field_mapping`: JSON-правила маппинга ответа на поля `UnifiedEvent` (`externalId`, `timestamp`, `preview`, `sourceType`)
  - `polling_interval_seconds`
- Реализуется как `GenericHttpConnector(BaseConnector)`.

**Webhook Receiver**
- Эндпоинт `POST /webhooks/{connector_id}` принимает push-события от любого сервиса.
- `connector_id` — ключ в реестре; коннектор должен быть зарегистрирован и иметь статус `active`.
- Опциональная HMAC-верификация подписи (секрет хранится в конфиге коннектора, не в коде).
- После верификации событие прогоняется через стандартный пайп: normalize → dedup → persist → audit.

**Что это даёт**
- Добавить новый источник = зарегистрировать коннектор (через UI или API), не писать Python.
- Внутренние корпоративные инструменты, CI-системы, кастомные алерты — всё первого класса.
- Встроенные коннекторы остаются для удобства (готовый маппинг полей), но не являются привилегированными.

**Порядок реализации**
1. Connector Registry API (CRUD на `/api/v1/connectors`) — Wave 1 optional / Sprint 3.
2. Generic HTTP Connector класс — Sprint 3.
3. Webhook Receiver эндпоинт — Sprint 3.
4. UI для добавления кастомных коннекторов — Sprint 4 / Wave 2.

## 6. Data and Compliance Rules

- Только официальные API/OAuth.
- Минимально необходимые scopes.
- Никакого серого парсинга веб-интерфейсов.
- Privacy-by-default UI (без скрытых трекеров взаимодействия).
- Явная политика хранения и удаления данных.

## 7. Design Baseline (Variant 1)

Рабочая база: secureinbox-design-spec.md.

Принципы:

- High-trust, cool-neutral визуальное направление.
- Ясная визуальная иерархия контента и системных метаданных.
- Privacy-first паттерны по умолчанию.
- WCAG AA обязательно.

Примечание: второй дизайн-файл будет рассмотрен как альтернатива, не как автоматическая замена.

## 8. Release Readiness Criteria

Готовность к релизу v1:

1. P0 функциональность завершена.
2. Security Gate полностью пройден.
3. Wave 1 Core интеграции работают стабильно.
4. Критичные UX error states покрыты.
5. Нагрузочное и smoke тестирование пройдено.

## 9. Change Policy

- Источники истины: файлы в docs/agent-answers/incoming + PROJECT_MASTER_BRIEF.md.
- Этот документ фиксирует согласованный baseline.
- Любые изменения scope/security/design вносятся через краткий changelog-блок с датой.
