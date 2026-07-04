# Unified Inbox — Техническая Архитектура

> **Статус:** RFC Draft v1.0 · **Дата:** 2026-06-25 · **Роль:** Staff Engineer

---

## Содержание

1. [Высокоуровневая архитектура](#1-высокоуровневая-архитектура)
2. [Unified Event Schema](#2-unified-event-schema)
3. [ADR — Architecture Decision Records](#3-adr--architecture-decision-records)
4. [Структура БД](#4-структура-бд)
5. [6-недельный план реализации](#5-план-реализации-на-6-недель)
6. [Технические риски и Mitigation](#6-технические-риски-и-mitigation)
7. [Приложения](#7-приложения)

---

## 1. Высокоуровневая архитектура

### 1.1 Диаграмма модулей

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                  │
│        Web SPA        │      Mobile App       │      REST / gRPC           │
└────────────────────────────────────────────────────────────────────────────┘
                                    │ HTTPS / WebSocket
┌────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                   │
│     JWT / OAuth2 Auth · Rate Limiting · Request Routing · TLS Term.        │
└────────────────────────────────────────────────────────────────────────────┘
          │                         │                          │
┌─────────┴────────┐   ┌────────────┴─────────┐   ┌──────────┴──────────┐
│  INBOX SERVICE   │   │    SYNC SERVICE       │   │  PLUGIN REGISTRY    │
│  Thread mgmt     │   │  Offline cache mgmt   │   │  Plugin loader      │
│  Labels / Tags   │   │  Conflict resolution  │   │  WASM sandbox       │
│  Full-text search│   │  Delta sync cursors   │   │  SDK versioning     │
└──────────────────┘   └──────────────────────┘   └─────────────────────┘
          │                         │                          │
┌────────────────────────────────────────────────────────────────────────────┐
│                               EVENT BUS                                    │
│   topic: raw.events · topic: normalized.events · topic: dlq · topic: audit │
│                   Redis Streams (primary) / Kafka (scale-out)              │
└────────────────────────────────────────────────────────────────────────────┘
     │                │                    │                    │
┌────┴──────┐  ┌──────┴─────────┐  ┌──────┴─────────┐  ┌──────┴──────────┐
│ CONNECTOR │  │ NORMALIZATION  │  │  ENCRYPTION    │  │  AUDIT LOG      │
│  LAYER    │  │    ENGINE      │  │   SERVICE      │  │   SERVICE       │
│           │  │                │  │                │  │                 │
│ Adapter   │  │ Schema valid.  │  │ KMS (envelope) │  │ Immutable       │
│ Registry  │  │ Field mapper   │  │ Key rotation   │  │ append-only     │
│           │  │ Dedup (hash)   │  │ Field-level    │  │ WORM storage    │
│ ──────── │  │                │  │ enc / dec      │  │                 │
│ Email     │  └────────────────┘  └────────────────┘  └─────────────────┘
│ Slack     │
│ Teams     │
│ SMS / WA  │
│ [Plugin]  │
└───────────┘
          │
┌────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE LAYER                                 │
│  PostgreSQL (RLS)  │  Redis Cluster (cache)  │  S3-compatible (attachments)│
│  Tenant isolation  │  Sync cursors · TTL     │  CDN + signed URLs         │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Описание модулей

| Модуль | Зона ответственности | Коммуникация |
|---|---|---|
| **API Gateway** | AuthN/AuthZ, rate limiting, маршрутизация, TLS termination | Входящий трафик → микросервисы |
| **Inbox Service** | Управление тредами, лейблами, поиском, пагинацией | REST/gRPC; читает из PostgreSQL |
| **Sync Service** | Offline cache, разрешение конфликтов, delta sync | WebSocket push; Redis cursors |
| **Plugin Registry** | Загрузка, версионирование, изоляция WASM-плагинов | Plugin SDK API; event bus subscription |
| **Event Bus** | Буферизация событий, гарантия доставки, топик-роутинг | Kafka / Redis Streams |
| **Connector Layer** | Адаптеры под каждый источник, polling/webhook | Публикует в `raw.events` |
| **Normalization Engine** | Валидация, маппинг, дедупликация, обогащение | Читает `raw.events` → пишет `normalized.events` |
| **Encryption Service** | Envelope encryption, key rotation, field-level dec/enc | Синхронный gRPC (low-latency) |
| **Audit Log Service** | Immutable append-only лог всех действий | Читает `topic: audit` |
| **Storage Layer** | PostgreSQL (RLS), Redis, S3 | Используется всеми сервисами |

---

## 2. Unified Event Schema

Все источники сериализуют события в единую обёртку. Схема версионирована.

```json
{
  "$schema": "unified-inbox/event/v1",
  "eventId": "uuid-v7",
  "tenantId": "uuid",
  "userId": "uuid",
  "sourceType": "email | slack | teams | sms | whatsapp | plugin:<name>",
  "sourceAccountId": "string",
  "externalId": "string",
  "threadId": "uuid",
  "parentEventId": "uuid | null",
  "timestamp": "ISO-8601 UTC",
  "receivedAt": "ISO-8601 UTC",
  "payload": {
    "subject": "string | null",
    "body": "string (encrypted field)",
    "bodyMimeType": "text/plain | text/html",
    "from": { "name": "string", "address": "string" },
    "to":  [ { "name": "string", "address": "string" } ],
    "cc":  [],
    "bcc": [],
    "attachments": [
      {
        "attachmentId": "uuid",
        "filename": "string",
        "mimeType": "string",
        "sizeBytes": "integer",
        "storageRef": "s3://bucket/path (encrypted)"
      }
    ],
    "metadata": {}
  },
  "flags": {
    "isRead": false,
    "isStarred": false,
    "isArchived": false,
    "importance": "low | normal | high"
  },
  "schemaVersion": "1.0.0",
  "checksum": "sha256-hex"
}
```

**Ключевые принципы схемы:**

- **UUID v7** как `eventId` — хронологически сортируемые, k-sortable для B-Tree индексации.
- **Encrypted fields** — `body` и `storageRef` шифруются до записи в bus и БД.
- **Checksum** — целостность проверяется на входе Normalization Engine.
- **Schema versioning** — мажорная версия в namespace (`/v1`, `/v2`). Backward-compatible эволюция через additive changes.
- `metadata` — свободный словарь для source-специфичных атрибутов без загрязнения core schema.

---

## 3. ADR — Architecture Decision Records

| ID | Контекст / Вопрос | Принятое решение | Рассмотренные альтернативы | Trade-offs и обоснование |
|---|---|---|---|---|
| **ADR-001** | Выбор технологии Event Bus | **Redis Streams** (старт); **Kafka** (scale-out path) | RabbitMQ, NATS JetStream, AWS SQS | Redis Streams: zero new infra, at-least-once delivery, consumer groups. Kafka: лучший throughput при >10 K msg/s, но требует KRaft overhead. Переход прозрачен через abstraction layer. RabbitMQ — сложнее replay. SQS — vendor lock-in. |
| **ADR-002** | Формат Unified Event Schema | **JSON Schema v7 + ajv validation** | Protobuf, Apache Avro, MessagePack | JSON: человекочитаем, прост для плагинов и SDK. Protobuf — быстрее на больших объёмах, но усложняет Plugin SDK (кодогенерация). Avro — schema registry overhead. На старте JSON достаточен; при >50 K msg/s — dual-write migration на Protobuf. |
| **ADR-003** | Модель изоляции тенантов | **Row-Level Security (RLS) + `tenant_id` column** | Schema-per-tenant, DB-per-tenant | RLS: один connection pool, простые миграции, линейно масштабируется до ~1 000 тенантов. Schema-per-tenant: изолированнее, но pg_connection overhead. DB-per-tenant: максимальная изоляция, но расточительно при SaaS с мелкими тенантами. RLS достаточно при аудите SQL-запросов. |
| **ADR-004** | Стратегия Offline Cache и Sync | **Event Sourcing + Delta Sync с cursor-based pagination** | CRDTs, Last-Write-Wins, OT | Event sourcing: точный replay, конфликты разрешаются детерминированно по timestamp + vector clock. LWW — прост, но теряет данные при конкурентных изменениях. CRDTs — избыточны для inbox (нет collaborative editing). OT — complexity overkill. Cursor хранится в Redis; offline state — в IndexedDB/SQLite на клиенте. |
| **ADR-005** | Стратегия шифрования | **Envelope Encryption (KMS) + Field-Level Encryption** | E2E шифрование, Full-disk шифрование | Envelope: Data Encryption Key (DEK) шифруется Key Encryption Key (KEK) в KMS. Ротация ключей без перешифровки данных. E2E — сервер не может делать поиск/индексирование. Full-disk — не защищает от утечек через приложение. Field-level для `body`, `address`, `storageRef`. |
| **ADR-006** | Изоляция Plugin SDK | **WebAssembly (WASM) sandbox** | Subprocess isolation, Native modules, V8 Isolates | WASM: детерминированное исполнение, memory-safe, capability-based (явные импорты). Subprocess — IPC overhead, OS-process leak риск. Native модули — критический риск: один баг роняет весь процесс. V8 Isolates — только JS/TS плагины. WASM позволяет Rust/C/Go/AssemblyScript SDK. |
| **ADR-007** | Дедупликация событий | **Content-addressable hash SHA-256 canonical payload** | eventId idempotency key, DB unique constraint only | Коннектор вычисляет `externalId + sourceType + timestamp` → SHA-256. Normalization Engine проверяет bloom filter (Redis) перед вставкой. DB unique constraint — вторая линия защиты. Только DB constraint недостаточно при высоком throughput (lock contention). |

---

## 4. Структура БД

### 4.1 Принципы многопользовательской модели

- Каждая таблица содержит `tenant_id UUID NOT NULL`.
- При открытии сессии устанавливается `SET LOCAL app.current_tenant_id = '...'`.
- RLS policy на каждой таблице: `USING (tenant_id = current_setting('app.current_tenant_id')::uuid)`.
- Superuser bypass (`BYPASSRLS`) — только для migration runner service account.

### 4.2 Схема таблиц

```sql
-- ─────────────────────────────────────────────────────
-- Тенанты (без RLS — системная таблица)
-- ─────────────────────────────────────────────────────
tenants
  id            UUID        PRIMARY KEY
  slug          TEXT        UNIQUE NOT NULL
  display_name  TEXT        NOT NULL
  plan          TEXT        -- 'free' | 'pro' | 'enterprise'
  settings      JSONB
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()

-- ─────────────────────────────────────────────────────
-- Пользователи
-- ─────────────────────────────────────────────────────
users
  id            UUID        PRIMARY KEY
  tenant_id     UUID        NOT NULL REFERENCES tenants(id)
  email         BYTEA       NOT NULL  -- field-encrypted
  display_name  TEXT
  role          TEXT        NOT NULL  -- 'owner' | 'admin' | 'member'
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
  [RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Коннекторы (источники)
-- ─────────────────────────────────────────────────────
connectors
  id            UUID        PRIMARY KEY
  tenant_id     UUID        NOT NULL
  user_id       UUID        REFERENCES users(id)
  source_type   TEXT        NOT NULL  -- 'email' | 'slack' | 'plugin:<name>'
  display_name  TEXT
  status        TEXT        NOT NULL  -- 'active' | 'paused' | 'error'
  config        JSONB       -- non-sensitive config
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
  [RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Учётные данные коннекторов (зашифрованы envelope)
-- ─────────────────────────────────────────────────────
connector_credentials
  id                UUID    PRIMARY KEY
  connector_id      UUID    NOT NULL REFERENCES connectors(id) ON DELETE CASCADE
  tenant_id         UUID    NOT NULL
  encrypted_payload BYTEA   NOT NULL  -- AES-256-GCM, зашифровано DEK
  dek_ref           TEXT    NOT NULL  -- ссылка на DEK в encryption_keys
  rotated_at        TIMESTAMPTZ
  [RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Треды (группировка сообщений)
-- ─────────────────────────────────────────────────────
threads
  id                   UUID    PRIMARY KEY
  tenant_id            UUID    NOT NULL
  user_id              UUID    NOT NULL REFERENCES users(id)
  connector_id         UUID    NOT NULL REFERENCES connectors(id)
  external_thread_id   TEXT                     -- ID треда в источнике
  subject              TEXT
  participant_addresses BYTEA                   -- field-encrypted JSONB array
  first_message_at     TIMESTAMPTZ
  last_message_at      TIMESTAMPTZ
  message_count        INTEGER  NOT NULL DEFAULT 0
  labels               UUID[]
  is_archived          BOOL     NOT NULL DEFAULT false
  is_starred           BOOL     NOT NULL DEFAULT false
  [RLS ENABLED]
  INDEX (tenant_id, user_id, last_message_at DESC)
  INDEX (tenant_id, connector_id)

-- ─────────────────────────────────────────────────────
-- Сообщения (ядро Unified Inbox)
-- ─────────────────────────────────────────────────────
messages
  id             UUID        PRIMARY KEY  -- UUID v7 (хронологически сортируемый)
  tenant_id      UUID        NOT NULL
  thread_id      UUID        NOT NULL REFERENCES threads(id)
  connector_id   UUID        NOT NULL REFERENCES connectors(id)
  external_id    TEXT        NOT NULL     -- ID в источнике
  dedup_hash     TEXT        NOT NULL     -- SHA-256 canonical hash
  source_type    TEXT        NOT NULL
  from_address   BYTEA       NOT NULL     -- field-encrypted
  to_addresses   BYTEA       NOT NULL     -- field-encrypted
  subject        TEXT
  body_ref       BYTEA                    -- зашифрованный S3 key
  body_preview   BYTEA                    -- первые 200 символов, encrypted
  schema_version TEXT        NOT NULL DEFAULT '1.0.0'
  flags          JSONB       NOT NULL DEFAULT '{}'
  received_at    TIMESTAMPTZ NOT NULL
  indexed_at     TIMESTAMPTZ
  [RLS ENABLED]
  UNIQUE (tenant_id, dedup_hash)
  INDEX (tenant_id, thread_id, received_at DESC)
  INDEX (tenant_id, connector_id, received_at DESC)

-- ─────────────────────────────────────────────────────
-- Вложения
-- ─────────────────────────────────────────────────────
attachments
  id           UUID    PRIMARY KEY
  tenant_id    UUID    NOT NULL
  message_id   UUID    NOT NULL REFERENCES messages(id) ON DELETE CASCADE
  filename     TEXT    NOT NULL
  mime_type    TEXT    NOT NULL
  size_bytes   BIGINT  NOT NULL
  storage_ref  BYTEA   NOT NULL  -- зашифрованный S3 path
  checksum     TEXT    NOT NULL  -- SHA-256 plaintext
  [RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Метки / Теги
-- ─────────────────────────────────────────────────────
labels
  id        UUID    PRIMARY KEY
  tenant_id UUID    NOT NULL
  user_id   UUID    REFERENCES users(id)
  name      TEXT    NOT NULL
  color     TEXT
  is_system BOOL    NOT NULL DEFAULT false  -- Inbox, Sent, Spam, Trash
  [RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Курсоры синхронизации (offline sync state)
-- ─────────────────────────────────────────────────────
sync_cursors
  id           UUID    PRIMARY KEY
  tenant_id    UUID    NOT NULL
  user_id      UUID    NOT NULL REFERENCES users(id)
  connector_id UUID    NOT NULL REFERENCES connectors(id)
  cursor_value TEXT    NOT NULL  -- source-specific (page token, timestamp, etc.)
  vector_clock JSONB   NOT NULL  -- {deviceId: seq} для conflict resolution
  synced_at    TIMESTAMPTZ NOT NULL DEFAULT now()
  [RLS ENABLED]
  UNIQUE (tenant_id, user_id, connector_id)

-- ─────────────────────────────────────────────────────
-- Ключи шифрования (Data Encryption Keys)
-- ─────────────────────────────────────────────────────
encryption_keys
  id             UUID    PRIMARY KEY
  tenant_id      UUID    NOT NULL
  key_purpose    TEXT    NOT NULL  -- 'messages' | 'credentials' | 'attachments'
  dek_ciphertext BYTEA   NOT NULL  -- DEK, зашифрованный KEK из KMS
  kek_ref        TEXT    NOT NULL  -- ссылка на KEK в KMS
  algorithm      TEXT    NOT NULL  -- 'AES-256-GCM'
  status         TEXT    NOT NULL  -- 'active' | 'rotating' | 'retired'
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
  retired_at     TIMESTAMPTZ
  [RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Аудит лог (append-only, INSERT-only RLS policy)
-- ─────────────────────────────────────────────────────
audit_log
  id            UUID    PRIMARY KEY
  tenant_id     UUID    NOT NULL
  actor_user_id UUID
  action        TEXT    NOT NULL  -- 'message.read' | 'connector.created' | ...
  resource_type TEXT    NOT NULL
  resource_id   UUID
  context       JSONB             -- IP, user-agent, session_id
  occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now()
  [RLS ENABLED; INSERT-ONLY POLICY]
```

### 4.3 RLS Policy (пример)

```sql
-- Установка контекста тенанта при открытии сессии
SET LOCAL app.current_tenant_id = :tenant_id;

-- Политика изоляции на таблице messages
CREATE POLICY tenant_isolation ON messages
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Audit log: только запись, без чтения через приложение
CREATE POLICY audit_insert_only ON audit_log
  FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### 4.4 ERD (упрощённая)

```
tenants ──< users ──< sync_cursors
                │
         ──< connectors ──< connector_credentials
                │
         ──< threads ──< messages ──< attachments
                │
         ──< labels
                │
         ──< encryption_keys
                │
         ──< audit_log
```

---

## 5. План реализации на 6 недель

### Обзор спринтов

| Спринт | Период | Цель | Key Deliverable |
|---|---|---|---|
| **Sprint 1** | Нед. 1–2 | Foundation & Infra | Event bus, base schema, CI/CD |
| **Sprint 2** | Нед. 2–3 | Connector Framework | 3 reference connectors (Email, Slack, Teams) |
| **Sprint 3** | Нед. 3–4 | Storage & Encryption | RLS, KMS, field-level enc, S3 |
| **Sprint 4** | Нед. 4–5 | Sync Engine | Offline cache, delta sync, conflict resolution |
| **Sprint 5** | Нед. 5–6 | Plugin SDK & API | WASM sandbox, SDK v1, public API |
| **Sprint 6** | Нед. 6 | Hardening | Pen test, load test, runbook, GDPR |

---

### Sprint 1 — Foundation & Infra (Нед. 1–2)

**Цель:** Минимальная сквозная инфраструктура.

| Задача | Приоритет | Результат |
|---|---|---|
| Redis Streams: топики, consumer groups, DLQ | P0 | Event bus функционирует |
| PostgreSQL: base schema + RLS policies + Flyway миграции | P0 | DB с изоляцией тенантов |
| API Gateway (Kong / Caddy + JWT middleware) | P0 | AuthN / AuthZ работают |
| Unified Event Schema v1.0 (JSON Schema + ajv) | P0 | Schema зафиксирована и версионирована |
| CI/CD pipeline (GitHub Actions: lint → test → docker build → staging deploy) | P1 | Автоматизированный деплой |
| Monitoring (Prometheus + Grafana: event lag, error rate, p99 latency) | P1 | Observability с day one |
| Базовый Normalization Engine (raw.events → validate → map → normalized.events) | P1 | Сквозной pipeline |

**DoD:** Событие, опубликованное в `raw.events`, появляется в `normalized.events` через < 200ms. RLS проверена integration-тестом.

---

### Sprint 2 — Connector Framework (Нед. 2–3)

**Цель:** Адаптерная модель + 3 reference connectors.

| Задача | Приоритет | Результат |
|---|---|---|
| ConnectorRegistry + BaseConnector interface (TypeScript/Python) | P0 | Расширяемый registry |
| EmailConnector (IMAP + SMTP, OAuth2 для Gmail / Outlook) | P0 | Получение email |
| SlackConnector (Events API + Socket Mode) | P0 | Slack события нормализуются |
| TeamsConnector (Microsoft Graph API webhooks) | P1 | Teams события нормализуются |
| Dedup Engine: bloom filter в Redis + DB unique constraint | P0 | Нет дублей при повторной доставке |
| Rate limiter per connector (token bucket, configurable) | P1 | API quota не превышается |
| Error handling: retry policy (exponential backoff + jitter), DLQ routing | P0 | Resilience при сбоях внешних API |

**DoD:** Email, Slack, Teams события нормализуются и сохраняются без дублей. DLQ наполняется при симуляции ошибок.

---

### Sprint 3 — Storage & Encryption (Нед. 3–4)

**Цель:** Безопасное хранение данных тенантов.

| Задача | Приоритет | Результат |
|---|---|---|
| KMS интеграция (AWS KMS primary / HashiCorp Vault fallback) | P0 | KEK управляется централизованно |
| Encryption Service: envelope encrypt/decrypt, DEK per tenant | P0 | Данные шифруются при записи |
| Field-level шифрование `body`, `from/to_addresses`, `storageRef` | P0 | PII защищён в покое |
| S3-compatible storage: upload, presigned URLs, CDN delivery | P1 | Вложения работают |
| Key rotation workflow (автоматический, zero-downtime dual-key period) | P1 | Ротация без простоя |
| Inbox Service: REST CRUD тредов, сообщений, labels (OpenAPI spec) | P0 | Основной API |
| Full-text search: PostgreSQL tsvector (fallback Meilisearch при росте) | P1 | Поиск по сообщениям |

**DoD:** Зашифрованные сообщения читаются авторизованным пользователем; cross-tenant isolation тест проходит; ротация ключей выполняется без downtime.

---

### Sprint 4 — Sync Engine (Нед. 4–5)

**Цель:** Offline-first клиент с надёжной синхронизацией.

| Задача | Приоритет | Результат |
|---|---|---|
| Sync Service: delta sync по cursor (Redis, TTL = 7d) | P0 | Клиент получает только diff |
| Vector clock для device-level conflict resolution | P0 | Конфликты разрешаются детерминированно |
| Client offline cache: IndexedDB (web) / SQLite (mobile) | P0 | Работа без сети |
| WebSocket push: real-time events на клиент (per-user channel) | P0 | Мгновенные уведомления |
| Conflict resolution strategy: server-wins + UI notification about conflict | P1 | Пользователь информирован |
| Background sync: Service Worker (web) / WorkManager (Android) | P1 | Незаметная фоновая синхронизация |
| Sync observability: consumer lag dashboard, stale cursor alerts | P2 | Операционная видимость |

**DoD:** Клиент без сети работает с кешем; после восстановления получает только delta-изменения; симуляция конфликта показывает корректное разрешение.

---

### Sprint 5 — Plugin SDK & Public API (Нед. 5–6)

**Цель:** Расширяемость системы и открытый API.

| Задача | Приоритет | Результат |
|---|---|---|
| Plugin SDK v1: BaseConnector WASM interface + capability whitelist | P0 | SDK задокументирован |
| WASM sandbox (Wasmtime): memory limit 64MB, CPU timeout 500ms | P0 | Изолированное выполнение плагина |
| Plugin Registry: загрузка, версионирование, health check, rollback | P0 | Плагины управляются |
| Plugin manifest.json: permissions, rate limits, schema, code signing | P1 | Явные capabilities |
| Reference plugin: TelegramConnector (эталонная реализация для разработчиков) | P1 | Пример для экосистемы |
| Public REST API v1: OpenAPI spec + API keys + per-key rate limiting | P0 | Внешние интеграции готовы |
| Developer portal: SDK docs, plugin publishing flow, changelogs | P2 | Ecosystem-ready |

**DoD:** Сторонний разработчик пишет коннектор-плагин по SDK и загружает его без изменений ядра; WASM isolation проверена fuzzing-тестом.

---

### Sprint 6 — Hardening (Нед. 6)

**Цель:** Production-ready качество.

| Задача | Приоритет | Результат |
|---|---|---|
| Penetration testing: OWASP Top 10, tenant isolation bypass, SSRF | P0 | Security report + закрытые findings |
| Load testing: 10 K событий/с, latency p99 < 500ms (k6 / Locust) | P0 | Performance baseline задокументирован |
| Chaos engineering: отказ Redis, PostgreSQL failover, KMS недоступен | P1 | SLA подтверждён экспериментально |
| Runbook: операционные процедуры, incident response, escalation paths | P0 | On-call готов к дежурству |
| API documentation: Swagger UI / Redoc, example requests | P0 | Docs complete |
| GDPR compliance: data deletion (crypto-shredding), data export (DSR) | P1 | Compliance audit passed |
| Dependency security audit (Snyk / Trivy): CVE-free baseline | P1 | Нет критических уязвимостей |

**DoD:** Прошёл pen test, нагрузочное и chaos тестирование; runbook задокументирован и пройден drill; GDPR deletion верифицирован.

---

## 6. Технические риски и Mitigation

| # | Риск | Вероятность | Impact | Mitigation |
|---|---|---|---|---|
| **R-01** | Schema evolution ломает существующих потребителей | Средняя | Высокий | Semantic versioning схемы; только additive changes в минорных версиях; contract testing (Pact) между producer и consumer |
| **R-02** | Rate limiting внешних API (Gmail: 250 quota units/user/s, Slack: 50 req/min) | Высокая | Средний | Token bucket per connector; jittered exponential backoff; приоритизация очереди; алерт при достижении 80% квоты |
| **R-03** | Утечка данных между тенантами через SQL-инъекцию или ошибку ORM | Низкая | Критический | RLS как last-resort барьер; parameterized queries обязательны; автоматизированные cross-tenant isolation тесты в CI; ежеквартальный pen test |
| **R-04** | Потеря DEK при сбое KMS → данные недоступны | Низкая | Критический | Multi-region KMS replicas; зашифрованный DEK backup в отдельном хранилище; runbook восстановления; ежеквартальный DR drill |
| **R-05** | Конфликты данных при offline sync — пользователь теряет данные | Средняя | Высокий | Сохранение обеих версий; UI уведомление о конфликте с возможностью manual resolution; полный event log для replay |
| **R-06** | Вредоносный WASM плагин — DoS или memory leak | Средняя | Высокий | Memory cap 64MB per plugin; CPU timeout 500ms; capability whitelist; обязательное code signing; плагины проходят security review перед публикацией |
| **R-07** | Redis Streams — потеря сообщений при падении до ACK | Средняя | Высокий | Consumer group + XACK только после успешной обработки; DLQ для failed messages; `WAIT` команда для durability; мониторинг consumer lag |
| **R-08** | GDPR right-to-erasure — сложность удаления зашифрованных данных | Средняя | Средний | Crypto-shredding: уничтожение DEK делает ciphertext недоступным; дополнительно hard delete для plaintext полей; audit trail удаления хранится отдельно |
| **R-09** | Vendor lock-in на облачный KMS | Средняя | Средний | Абстракция `KMSProvider` interface; поддержка HashiCorp Vault (self-hosted) как fallback с первого дня |
| **R-10** | Деградация full-text search при росте БД (>100M строк) | Средняя | Средний | `tsvector` индекс + периодический REINDEX; при >100M строк — выделенный Meilisearch; партиционирование по `tenant_id` + `received_at` |

---

## 7. Приложения

### A. Connector Adapter Interface (Pseudocode)

```typescript
interface ConnectorManifest {
  sourceType: string
  version:    string
  capabilities: Array<'read' | 'send' | 'webhook'>
  rateLimits: { requestsPerSecond: number }
  requiredPermissions: string[]
}

interface BaseConnector {
  readonly sourceType: string
  readonly manifest:   ConnectorManifest

  authenticate(credentials: EncryptedCredentials): Promise<AuthContext>
  fetchEvents(cursor: SyncCursor): AsyncIterator<RawEvent>
  handleWebhook?(payload: unknown): RawEvent | null
  sendMessage?(draft: MessageDraft): Promise<ExternalId>

  onError(error: ConnectorError): RetryPolicy
  healthCheck(): Promise<HealthStatus>
}
```

### B. Plugin Manifest Schema

```json
{
  "pluginId": "com.example.telegram-connector",
  "version": "1.2.0",
  "sourceType": "plugin:telegram",
  "capabilities": ["read_messages", "send_messages"],
  "requiredPermissions": ["network.api.telegram.org", "storage.read"],
  "rateLimits": { "requestsPerSecond": 30 },
  "wasmModule": "connector.wasm",
  "checksum": "sha256:a3f5c2..."
}
```

### C. Deployment Topology (Production)

```
Kubernetes Cluster:
  API Gateway          — 2+ pods,  HPA (CPU 60%)
  Inbox Service        — 3+ pods,  HPA
  Sync Service         — 3+ pods,  stateless, HPA
  Normalization Engine — 3+ pods,  HPA (consumer lag-based)
  Connector Runner     — per-connector Deployment, restartPolicy: Always
  Encryption Service   — 2+ pods   (low latency SLA, no aggressive HPA)
  Plugin Registry      — 2+ pods

Data:
  PostgreSQL           — Primary + 2 Read Replicas + PgBouncer
  Redis Cluster        — 3 shards × 2 replicas
  S3                   — Multi-region replication, versioning ON
  KMS                  — AWS KMS multi-region OR Vault HA cluster
```

### D. Key Metrics & SLOs

| Метрика | Target |
|---|---|
| Event pipeline latency (raw → normalized) | p99 < 500ms |
| API Gateway response time | p99 < 200ms |
| Offline sync delta delivery | < 5s after reconnect |
| Message dedup false-negative rate | < 0.001% |
| Encryption/decryption overhead | < 5ms per field |
| Uptime (API Gateway + Inbox Service) | 99.9% monthly |
| RTO (Recovery Time Objective) | < 30 min |
| RPO (Recovery Point Objective) | < 5 min |

---

*Документ подготовлен в рамках технического RFC. Все ADR требуют ревью команды перед финализацией архитектуры.*
