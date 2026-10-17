# ALLinO — Project Review

Date: 2026-07-01 (updated from 2026-06-25)

---

## Changelog

### 2026-07-01 — Post-review fixes (verified)

| Was                                                             | Fix                                                                         |
| --------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `/metrics` отдавал агрегаты без tenant scope                    | `ingestion_metrics` теперь tenant-scoped через `Depends(resolve_tenant_id)` |
| MetricsStore смешивал метрики всех tenant                       | `MetricsStore` хранит и отдает данные по `tenant_id`                        |
| S2-08 DoD: filter state в сессии не сохранялся                  | `frontend/src/app/page.tsx` сохраняет `mode` + `filters` в `sessionStorage` |
| SPRINT2 board показывал `Ready to execute` при закрытом спринте | Статус обновлен на `Closed (выполнено)`                                     |

### 2026-06-30 — Security hardening sprint (verified against code)

Fixed items from the 2026-06-25 review:

| Was                                                          | Fix                                                             |
| ------------------------------------------------------------ | --------------------------------------------------------------- |
| §2.1 `security.py` / `config.py` пустые                      | Реализованы: `ALLINO_API_KEY` + `require_api_key` dependency    |
| §2.3 `/events`, `/validate` без `Depends(resolve_tenant_id)` | Добавлен `Depends(resolve_tenant_id)` на оба эндпоинта          |
| §2.4 `tenantId` в теле не сверяется с заголовком             | `_assert_tenant_match()` + silent reject в batch                |
| §2.6 `/seed` без авторизации                                 | `Depends(resolve_tenant_id)` добавлен                           |
| §3.3 Нет root `.gitignore`                                   | `.gitignore` добавлен в корень                                  |
| §3.4 Миграции без трекинга                                   | `schema_migrations` таблица, `init_db()` пропускает применённые |
| §3.5 Дублирование в connector sync                           | `_process_connector_batch()`                                    |
| §3.7 Нет индекса на `audit_logs`                             | `0003_hardening.sql` → `idx_audit_logs_tenant_time`             |
| §3.8 `limit` не ограничен                                    | `Query(ge=1, le=1000)` на `/inbox`, `/audit`, `/seed`           |
| §4.1 `extra="allow"` на UnifiedEvent                         | `extra="forbid"`                                                |
| §4.2 CORS `["*"]`                                            | Сужен до `GET, POST` + явный список заголовков                  |
| §4.3 `tenant_id` как query param во фронте                   | `X-Tenant-Id` заголовок                                         |
| §4.5 `@on_event("startup")` устарел                          | `lifespan` context manager                                      |
| §5.5 `InboxMessage` без `priority`                           | Поле `priority: Literal["high","medium","normal"]` добавлено    |
| §6.1 `BACKEND_URL` захардкожен                               | Читается из `NEXT_PUBLIC_BACKEND_URL` env var                   |
| §6.3 Inline стили вместо design system                       | Redesign: CSS tokens, 3-panel layout, Tailwind                  |

---

## 1. Общий статус

Sprint 2, бэкенд работает end-to-end.
Три коннектора (GitHub, GitLab, Linear) реализованы на уровне scaffold + smoke.
Security hardening выполнен частично: API-key auth, tenant isolation, CORS, migration tracking — внесены.
**Главный незакрытый долг: auth без ALLINO_API_KEY в env = полностью открытый dev-режим. JWT не реализован.**

---

## 2. Критические проблемы (блокеры)

### 2.1 Auth работает только при установленном `ALLINO_API_KEY`

`require_api_key` (security.py:20): если env var не установлен — зависимость возвращает `None` без проверки.
Это значит, что в любой среде без явно выставленного секрета все эндпоинты открыты.
Security Gate требует JWT hardening. API key — промежуточное решение, не финальное.

```python
# security.py:20
if not ALLINO_API_KEY:
    return  # dev mode — no key configured, skip enforcement
```

Риск: любой разработчик, запустивший backend без `.env`, получает незащищённую инстанцию.

### 2.2 Audit log не является append-only на уровне БД

`0001_init.sql` не содержит триггера `BEFORE UPDATE/DELETE` на `audit_logs`.
В SQLite нет RLS (`0002_rls.sql` — no-op по замыслу).
`audit_logs` — обычная таблица, любой код может делать UPDATE/DELETE на ней.
Security Gate требует append-only audit — это не выполнено.

---

## 3. Архитектурные проблемы

### 3.1 Redis Streams отсутствует — события обрабатываются синхронно в запросе

CLAUDE.md § 5: _"Event bus start path: Redis Streams"_.
В реальности fetch → normalize → dedup → persist — всё в теле HTTP-запроса.
Нет очереди, нет back-pressure, нет retry отдельных событий.
При медленном upstream запрос блокируется.

### 3.2 Docker compose baseline — закрыто

`docker-compose.yml` присутствует, backend/frontend сервисы запускаются,
добавлены healthcheck и build args для `NEXT_PUBLIC_*`.

### 3.3 Мёртвые таблицы в схеме БД

`0001_init.sql` создаёт четыре таблицы; используются только две:

| Таблица      | Репозиторий                 |
| ------------ | --------------------------- |
| `messages`   | ✅ `messages_repo.py`       |
| `audit_logs` | ✅ `audit_repo.py`          |
| `users`      | ❌ нет репозитория, нет API |
| `connectors` | ❌ нет репозитория, нет API |

Примечание: `connectors` упомянута в Connector Registry архитектуре (CLAUDE.md § 5), но репозитория нет.

### 3.4 `domain/models.py` — пустой файл

Доменные модели живут в [domain/events.py](../../backend/app/domain/events.py).
[domain/models.py](../../backend/app/domain/models.py) — 1 строка.
Следующий агент/разработчик может начать писать модели туда и создать раскол в доменном слое.

---

## 4. Несоответствия между планом и реализацией

### 4.1 Расхождение Wave 1 Core между документами

| Источник                     | Wave 1 Core                            |
| ---------------------------- | -------------------------------------- |
| CLAUDE.md § 3                | GitHub, GitLab, Jira, Linear, Telegram |
| PROJECT_MASTER_BRIEF § 1.2.C | GitHub, GitLab, Jira, Linear, Telegram |
| Sprint 2 выбор               | GitHub, GitLab, Linear                 |

Jira и Telegram заявлены Wave 1 Core в двух документах, не вошли в Sprint 2. Решение не задокументировано.

### 4.2 Sprint 2 exit criteria — частично не выполнены

| Критерий                                   | Статус                                                              |
| ------------------------------------------ | ------------------------------------------------------------------- |
| 3 интеграции стабильно ingest события      | ✅                                                                  |
| Inbox: приоритеты и фильтры (S2-06, S2-08) | ❌ не начаты (поле `priority` добавлено в модель, classifier — нет) |
| Thread linking показывает контекст (S2-07) | ❌ `threads_repo.py` пуст                                           |
| Error/empty states (S2-09)                 | ❌ не начато                                                        |
| Security Gate не деградирован              | ⚠️ частично — auth реализован, JWT отсутствует                      |

### 4.3 `test_ingestion_idempotency.py` пуст

Файл существует, тест не написан.
Задача S2-05 помечена in progress, но реального покрытия нет.

### 4.4 `threads_repo.py` пуст, `ThreadPanel` без данных

Таблица `threads` в `0001_init.sql` есть.
`threads_repo.py` — пуст. `ThreadPanel` во фронте показывает один item без связанных событий.

---

## 5. Проблемы безопасности (не блокеры)

### 5.1 Токены в JSON body попадают в access logs

`GitHubSyncRequest.token`, `LinearSyncRequest.token`, `GitLabSyncRequest.token` — в JSON body.
Log sanitization не реализован.
Security blueprint T-07: _"Tokens only in headers/body, log sanitization"_ — sanitization часть не выполнена.

---

## 6. Проблемы фронтенда

### 6.1 Режимы (focus/incident) не влияют на список сообщений

`mode` state переключается через `ModeToggle`, но `InboxList` получает те же `items` независимо от режима.
Focus Mode и Incident Mode — это просто label, не функционал.

### 6.2 Нет CI для фронтенда

`.github/workflows/backend-ci.yml` покрывает только бэкенд.
Нет `npm run build` проверки, нет `tsc --noEmit`, нет линтера для фронтенда.

---

## 7. Мелкие неточности

### 7.1 Cursor pagination — просто integer index

В коннекторах `cursor` трактуется как `int(cursor)` для слайса в памяти. Не работает для реального GitHub API (cursor — opaque string из Link header).

### 7.2 `urllib` вместо `httpx` для HTTP-запросов

`httpx` уже в `requirements-dev.txt`. Коннекторы используют `urllib.request`. Нет timeout на уровне read, нет удобной обработки HTTP-статусов.

### 7.3 CI запускает ruff только на pyflakes (`--select F`)

Полный linting (style, type annotations, security) не проверяется.

### 7.4 Зависимости без Dependabot

Версии закреплены вручную. Нет автоматического обновления.

---

## 8. Предложения по приоритизации (Sprint 3)

| #   | Что                                                      | Статус               | Почему                                                  |
| --- | -------------------------------------------------------- | -------------------- | ------------------------------------------------------- |
| 1   | `test_ingestion_idempotency.py`                          | ✅ закрыт (S2-05)    | 7 тестов: unit + API-level                              |
| 2   | Priority Classifier + фильтры в inbox                    | ✅ закрыт (S2-06/08) | `priority_classifier.py`, `FilterBar.tsx`               |
| 3   | Thread context linking                                   | ✅ закрыт (S2-07)    | relatedItems по source в ThreadPanel                    |
| 4   | Error/empty states на фронте                             | ✅ закрыт (S2-09)    | loading, error banner, empty filter state               |
| 5   | `docker-compose.yml`                                     | ✅ закрыт (W1-08)    | ALLINO_API_KEY env, NEXT_PUBLIC build args, healthcheck |
| 6   | CI для фронтенда                                         | ✅ закрыт            | `frontend-ci.yml`: typecheck + production build         |
| 7   | `domain/models.py` пустой файл                           | ✅ уже отсутствует   | удалён до начала сессии                                 |
| 8   | Добавить триггер BEFORE UPDATE/DELETE на `audit_logs`    | ❌ открыт            | Append-only на уровне БД, не только кода                |
| 9   | Реализовать `connectors` репозиторий или удалить таблицу | ❌ открыт            | Schema drift; `connectors` в архитектуре CLAUDE.md § 5  |
| 10  | Log sanitization для токенов в connector requests        | ❌ открыт            | security blueprint T-07                                 |

---

## 9. Что сделано хорошо

- Unified Event Schema соблюдается во всех трёх коннекторах.
- Dedup через SHA-256 hash — правильный подход.
- Connector base class с lifecycle hooks (`start/stop/health`) и retry policy.
- Tenant-scoped reads в репозиториях (SQL WHERE tenant_id = ?).
- `BaseConnector.run_with_retry` с backoff.
- CORS origins читаются из env var.
- `schema_migrations` — миграции применяются один раз.
- `extra="forbid"` на UnifiedEvent — unknown fields → 422.
- `lifespan` context manager — deprecated API убран.
- `_process_connector_batch()` — DRY connector sync loop.
- Design system: CSS tokens, 3-panel layout, WCAG AA baseline.
- `X-Tenant-Id` заголовок во фронте + env-var BACKEND_URL.
- `limit` clamped `ge=1, le=1000`.
- CI workflow существует и запускается при push/PR.
- `test_tenant_isolation.py` изолирован через `tmp_path`.
- CURRENT_STATE.md поддерживается актуально.
