# ALLinO: Master Brief (до начала кодинга)

Этот файл — единая точка управления проектом.
Цель: спланировать безопасный unified inbox для разработчиков и удаленных команд
с поэтапной поддержкой ответов (двусторонней коммуникации) через официальные API.

## 0) Что мы строим

Продукт: единый inbox, который собирает события из рабочих источников (Slack/Discord/GitHub/Jira и т.д.) в одном интерфейсе.

Важно про ответы:

- В MVP допускается read-first подход (сбор и приоритизация входящих).
- Reply/action-функции добавляются поэтапно только там, где это безопасно и стабильно поддержано официальным API.

Ключевой принцип:

- Security-first + Privacy-first + Local-first.

Нельзя нарушать:

1. Никаких серых интеграций и парсинга веб-интерфейсов.
2. Только официальные API/OAuth.
3. Минимальные права доступа (least privilege).
4. Токены/секреты только в защищенном хранилище и шифровании.
5. Прозрачные логи доступа и контроль удаления данных.

---

## 1) Порядок работы с ИИ-агентами

Иди строго по очереди. Не перескакивай.

1. Product Strategist
2. Security Architect
3. API Integrations Architect
4. UX/IA Architect
5. Technical Architect
6. Design System (Claude)

После каждого шага копируй ответ агента в раздел "Ответ агента" ниже.

### 1.1) Каноничные файлы ответов

Для шагов 1-3 используем как главный источник отдельные файлы в папке
[docs/agent-answers/incoming](docs/agent-answers/incoming).

| Шаг                           | Файл                                                                                                                               | Статус   |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | -------- |
| 1. Product Strategist         | [docs/agent-answers/incoming/unified-inbox-strategy-v2.md](docs/agent-answers/incoming/unified-inbox-strategy-v2.md)               | Загружен |
| 2. Security Architect         | [docs/agent-answers/incoming/security-blueprint-unified-inbox.md](docs/agent-answers/incoming/security-blueprint-unified-inbox.md) | Загружен |
| 3. API Integrations Architect | [docs/agent-answers/incoming/unified-inbox-integration-matrix.md](docs/agent-answers/incoming/unified-inbox-integration-matrix.md) | Загружен |
| 4. UX/IA Architect            | [docs/agent-answers/incoming/unified-inbox-ux-ia.md](docs/agent-answers/incoming/unified-inbox-ux-ia.md)                           | Загружен |
| 5. Technical Architect        | [docs/agent-answers/incoming/unified-inbox-architecture.md](docs/agent-answers/incoming/unified-inbox-architecture.md)             | Загружен |
| 6. Design System (variant 1)  | [docs/agent-answers/incoming/secureinbox-design-spec.md](docs/agent-answers/incoming/secureinbox-design-spec.md)                   | Загружен |

### 1.2) Нормализация v1 (шаги 1-3)

Этот блок фиксирует согласованные решения по текущим ответам.
Исходные файлы в [docs/agent-answers/incoming](docs/agent-answers/incoming) не редактируются.

#### A. Product/Scope baseline

1. Режим продукта на старте: local-first, self-hosted-first, read-first.
2. Ответы (reply/action) не входят в P0, добавляются поэтапно после security-gate.
3. Никаких неофициальных интеграций и веб-скрейпинга; только официальные API/OAuth.

#### B. Security baseline (из шага 2, адаптировано под scope)

1. Для MVP применяем P0-контроли из security blueprint как обязательные (JWT hardening, tenant isolation, encryption at rest, CSP/HSTS, Vault, MFA, audit append-only, rate limits).
2. Формулировки cloud-native/multi-tenant трактуем как target-архитектуру для cloud-режима, не как обязательный режим первой локальной поставки.
3. Провайдеры Gmail/Outlook считаются out-of-scope для текущего MVP и не являются блокером.

#### C. Интеграции: итоговая приоритизация (снятие конфликтов шага 1 и 3)

1. Wave 1 Core (обязательно): GitHub, GitLab, Jira, Linear, Telegram.
2. Wave 1 Optional (если успеваем без роста риска): Slack (только свой workspace), Google Calendar/Meet (с авто-renew watch channels).
3. Wave 2: Discord (полный режим), Zoom, Teams, hardening Slack/Google Calendar.
4. Wave 3: Rocket.Chat, WhatsApp Business, Viber.

#### D. Правило истинности

1. Детали и обоснования храним в каноничных файлах шага 1-3.
2. В этом master-файле фиксируем только согласованное решение и изменения статуса.

### 1.3) Нормализация v2 (шаги 4-6)

Этот блок фиксирует согласованные решения по UX, архитектуре и первому дизайн-варианту.
Исходные файлы в [docs/agent-answers/incoming](docs/agent-answers/incoming) не редактируются.

#### A. UX/IA baseline

1. Основная оболочка: Unified Inbox как точка входа по умолчанию.
2. Базовые L1-разделы: Inbox, Focus Mode, Incident Mode, Security Center, Settings.
3. Thread View открывается как overlay/panel, а не как отдельное тяжелое приложение внутри приложения.
4. Режимы Focus и Incident трактуем как состояния оболочки, а не как отдельные продуктовые вертикали.
5. Онбординг должен требовать подключение минимум одного источника, но не блокировать пользователя навсегда при Skip.

#### B. UX ограничения для MVP

1. Quick Reply допускается в UX как будущий путь, но не считается обязательной функцией P0.
2. Приоритеты должны объясняться интерфейсом и быть переопределяемыми пользователем.
3. Empty states и error paths обязательны для первого релиза, особенно для connect-source, rate limit и sync interruptions.

#### C. Technical architecture baseline

1. Архитектурный стиль: модульная сервисная архитектура с Connector Layer, Normalization Engine, Encryption Service, Audit Log Service.
2. Unified Event Schema принимаем как обязательный контракт между коннекторами и остальной системой.
3. Tenant isolation: RLS + tenant_id остается базовым решением для общей модели данных.
4. Event Bus: стартуем с Redis Streams как primary path; Kafka рассматриваем только как scale-out path.
5. Plugin SDK: сохраняем направление на WASM sandbox, но не делаем его блокером первой поставки.
6. Sync strategy: cursor-based delta sync с offline cache принимается как базовый подход.
7. **Extensible Connector Architecture (решено 2026-06-30):** система коннекторов спроектирована как открытая платформа. Три компонента: (a) Connector Registry — реестр всех коннекторов в БД; (b) Generic HTTP Connector — универсальный коннектор для любого REST API, конфигурируемый без написания кода; (c) Webhook Receiver — `POST /webhooks/{connector_id}` для push-событий. Встроенные коннекторы — предустановленные профили поверх той же механики. Детальный design в PREBUILD_SPEC_V1.md § 5.1.

#### D. Technical scope guard

1. Техническая архитектура из шага 5 трактуется как target architecture, не обязательная полнота первой локальной версии.
2. Для первой поставки допускается упрощенная реализация, если она не ломает security baseline и unified event contract.
3. Attachment storage, advanced mobile flows и full plugin marketplace не считаются P0.

#### E. Design baseline (variant 1)

1. Визуальное направление: high-trust, cool-neutral, без "hacker"-эстетики и без шумного dark-mode-first дизайна.
2. Принимаем privacy-first паттерны интерфейса: initials-only avatars по умолчанию, блокировка remote assets, opt-in для preview/read receipts.
3. Сигнатурный паттерн Trust-Lines считаем сильным кандидатом на основной визуальный маркер безопасности.
4. Типографика и визуальная иерархия должны явно разделять человеческий контент и системные/криптографические метаданные.
5. Accessibility WCAG AA и restrained motion считаются обязательными требованиями, а не polish-задачами.

#### F. Статус шага 6

1. Текущий файл дизайна считаем variant 1, а не окончательным финалом.
2. Второй дизайн-файл будет сравниваться как альтернативный источник; до его появления variant 1 используем как рабочую базу.

#### G. Итоговая рабочая рамка после шагов 1-6

1. Продукт первой версии: secure, reading-first unified inbox для разработчиков и удаленных команд.
2. Ядро MVP: подключение источников, сбор/нормализация событий, приоритизация, thread context, focus/incident modes, security center visibility.
3. Не-P0: полнофункциональный write-back, облачные фичи ради удобства, широкая экосистема плагинов, второй и третий класс интеграций.

### 1.4) Execution Docs

1. Pre-build baseline: [docs/planning/PREBUILD_SPEC_V1.md](docs/planning/PREBUILD_SPEC_V1.md)
2. Sprint plan (W1-W2): [docs/planning/SPRINT_PLAN_W1_W2.md](docs/planning/SPRINT_PLAN_W1_W2.md)
3. Sprint 1 task board: [docs/planning/SPRINT1_TASK_BOARD.md](docs/planning/SPRINT1_TASK_BOARD.md)
4. Sprint 2 task board: [docs/planning/SPRINT2_TASK_BOARD.md](docs/planning/SPRINT2_TASK_BOARD.md)
5. Kickoff checklist: [docs/planning/IMPLEMENTATION_KICKOFF_CHECKLIST.md](docs/planning/IMPLEMENTATION_KICKOFF_CHECKLIST.md)
6. Sprint 1 scaffolding plan: [docs/planning/SPRINT1_SCAFFOLDING_PLAN.md](docs/planning/SPRINT1_SCAFFOLDING_PLAN.md)
7. AI agent rules: [CLAUDE.md](CLAUDE.md)
8. Dev quickstart: [docs/planning/DEV_QUICKSTART.md](docs/planning/DEV_QUICKSTART.md)
9. Smoke runbook: [docs/planning/SMOKE_RUNBOOK.md](docs/planning/SMOKE_RUNBOOK.md)
10. Current state handoff: [docs/planning/CURRENT_STATE.md](docs/planning/CURRENT_STATE.md)
11. Agent start template (60 sec): [docs/planning/AGENT_START_TEMPLATE.md](docs/planning/AGENT_START_TEMPLATE.md)

---

## 2) Готовые промпты (копировать как есть)

### Шаг 1: Product Strategist

Промпт:

Ты product strategist для B2B SaaS. Спроектируй концепцию unified inbox приложения для разработчиков и удаленных команд.

Контекст:

- Приложение агрегирует сообщения и уведомления из рабочих систем (Slack, Discord, GitHub, GitLab, Jira, Linear, Teams, Zoom, Telegram и т.д.).
- Приоритет: безопасность и приватность выше скорости разработки.
- Стратегия: сначала planning, потом код.

Сделай:

1. ICP-сегменты (кто пользователи) и топ-7 болей.
2. Job stories (минимум 10).
3. Топ-12 возможностей MVP и анти-фичи (что НЕ делать в MVP).
4. Метрики успеха (30/90 дней).
5. Роадмап на 3 волны (Wave 1/2/3).

Формат:

- Коротко, структурно, с таблицами.
- Без воды и без общих фраз.

#### Ответ агента (вставь сюда)

Каноничный источник для шага 1:
[docs/agent-answers/incoming/unified-inbox-strategy-v2.md](docs/agent-answers/incoming/unified-inbox-strategy-v2.md)

# Unified Inbox — Product Strategy v2

> Local-first · Free APIs only · No vendor negotiations  
> Stack: Python FastAPI · React/Next.js · SQLite · Docker

---

## Ограничения как преимущества

| Ограничение               | Как переформулировать                                       |
| ------------------------- | ----------------------------------------------------------- |
| Нет партнёрских API       | "Работает с твоим PAT — никаких корпоративных согласований" |
| Данные только локально    | "Твои уведомления не уходят ни в какое облако"              |
| Open source / self-hosted | "Ставишь через Docker за 2 минуты и владеешь всем"          |
| Только открытые API       | "Работает там, где разработчик и так уже есть"              |

---

## 1. ICP-сегменты

| Сегмент                         | Размер | Стек                                       | WTP                                |
| ------------------------------- | ------ | ------------------------------------------ | ---------------------------------- |
| Indie Developer / Freelancer    | 1      | GitHub, GitLab, Telegram, Linear           | $0 (self-hosted) → $6–10/мес cloud |
| Privacy-conscious Engineer      | 1–5    | GitHub, GitLab, Discord, Jira              | self-hosted, donate / sponsor      |
| Small Remote Team (no IT dept.) | 5–15   | GitHub + Linear + Telegram + Discord       | $10–20/мес/seat                    |
| DevOps / Platform Engineer      | any    | GitLab CI, GitHub Actions, Telegram alerts | self-hosted, enterprise later      |

> **Сдвиг ICP относительно v1:** убираем корпоративных покупателей из Wave 1.  
> Наш первый пользователь — разработчик, который сам себе DevOps и сам платит.

### Топ-7 болей (скорректированы)

| #   | Боль                                                                                 | Интенсивность | Частота             |
| --- | ------------------------------------------------------------------------------------ | ------------- | ------------------- |
| 1   | 8–12 вкладок одновременно: GitHub, GitLab, Telegram, Linear, Jira, Discord           | 🔴 Критичная  | Ежедневно           |
| 2   | PR-ревью, упомянутый issue и Telegram-алерт — три разных приложения об одном событии | 🔴 Критичная  | Несколько раз/день  |
| 3   | Важный GitHub notification тонет среди Dependabot и CI-спама                         | 🔴 Критичная  | Ежедневно           |
| 4   | Нет связи issue ↔ PR ↔ сообщение в Telegram/Discord                                  | 🟠 Высокая    | Ежедневно           |
| 5   | Все существующие инструменты агрегации требуют облачного доступа к токенам           | 🟠 Высокая    | Постоянно (доверие) |
| 6   | Context switching убивает flow — GitLab CI упал, надо открыть 4 источника            | 🟠 Высокая    | Ежедневно           |
| 7   | Нет единой точки для stand-up: что я вообще делал вчера?                             | 🟡 Средняя    | Ежедневно           |

---

## 2. Job Stories

| #     | Ситуация                                 | Мотивация                                                                      | Ожидаемый результат                                |
| ----- | ---------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------- |
| JS-01 | Когда начинаю рабочий день               | хочу видеть pending actions из GitHub, GitLab, Linear и Telegram в одном месте | планирую день за 3 минуты без открытия 6 вкладок   |
| JS-02 | Когда вхожу в deep work                  | хочу отключить некритичные уведомления одним действием                         | работаю 90+ минут без прерываний                   |
| JS-03 | Когда мне назначен PR-ревью на GitHub    | хочу видеть связанный Linear-issue и предыдущие комментарии прямо здесь        | даю ревью без переключения контекста               |
| JS-04 | Когда падает GitLab CI                   | хочу один алерт вместо трёх (email + Slack-бот + Telegram)                     | не собираю картину по трём каналам                 |
| JS-05 | Когда возвращаюсь после митинга          | хочу быстро просмотреть что пропустил, отфильтровав по важности                | возвращаюсь в работу за 5 минут                    |
| JS-06 | Когда настраиваю инструмент              | хочу вставить PAT и через минуту видеть уведомления                            | не регистрирую OAuth-приложения и не жду одобрения |
| JS-07 | Когда думаю об использовании инструмента | хочу чтобы мои токены и сообщения не уходили в чужое облако                    | могу подключить рабочие аккаунты без параноии      |
| JS-08 | Когда on-call                            | хочу чтобы critical Telegram-алерты были отделены от GitHub-шума               | не пропускаю инциденты                             |
| JS-09 | Когда менеджер просит статус             | хочу auto-summary активности по GitHub + Linear за последние 24ч               | отвечаю за 30 секунд без ручного составления       |
| JS-10 | Когда заканчиваю задачу                  | хочу снуз всех связанных уведомлений одним действием                           | не получаю алерты о закрытой теме                  |
| JS-11 | Когда хочу поставить коллеге             | хочу скинуть docker-compose.yml и всё                                          | коллега разворачивает за 2 минуты без инструкций   |
| JS-12 | Когда работаю с двух машин               | хочу синхронизацию read-статуса (опционально через свой сервер)                | не читаю одно и то же дважды                       |

---

## 3. Топ-12 возможностей MVP + Анти-фичи

### Интеграции Wave 1 — только бесплатные API без переговоров

| Источник     | Метод                          | Статус                            |
| ------------ | ------------------------------ | --------------------------------- |
| **GitHub**   | PAT или GitHub App (бесплатно) | ✅ Wave 1                         |
| **GitLab**   | Personal Access Token          | ✅ Wave 1                         |
| **Telegram** | Bot API (BotFather, 2 мин)     | ✅ Wave 1                         |
| **Linear**   | API key в настройках           | ✅ Wave 1                         |
| **Jira**     | API token (Atlassian account)  | ✅ Wave 1                         |
| **Discord**  | Bot API (Developer Portal)     | ✅ Wave 1                         |
| Slack        | требует workspace admin        | 🟡 Wave 2 (только свой workspace) |
| Teams        | Azure app registration         | 🔴 Wave 3 (по demand)             |

### MVP Features — приоритет по Value/Effort

| P   | Фича                                                             | Value   | Effort | Обоснование                                   |
| --- | ---------------------------------------------------------------- | ------- | ------ | --------------------------------------------- |
| P0  | PAT-based подключение: GitHub, GitLab, Telegram, Linear, Jira    | Core    | S      | Никаких OAuth-серверов, работает сразу        |
| P0  | Read-only агрегация в локальный SQLite                           | Core    | M      | Данные не уходят никуда — это фича            |
| P0  | Smart deduplication (одно событие → одна карточка)               | Core    | M      | Убивает боль #2                               |
| P1  | Priority classifier rule-based (тип + источник + ключевые слова) | High    | S      | Решает боль #3 без AI                         |
| P1  | Thread context stitching: GitHub issue ↔ PR ↔ Telegram-алерт     | High    | L      | Главный дифференциатор                        |
| P1  | Focus Mode / DND с расписанием                                   | High    | S      | Решает боль #6                                |
| P1  | Keyboard-first навигация + command palette                       | High    | S      | Developer UX, high NPS driver                 |
| P2  | Universal search по всем источникам (локальный FTS в SQLite)     | Medium  | M      | Всё на месте, никаких cloud search API        |
| P2  | Snooze / defer уведомлений                                       | Medium  | S      | Стандарт для inbox-продуктов                  |
| P2  | Custom notification rules / filters                              | Medium  | M      | Решает боль #5                                |
| P2  | Read status sync across devices                                  | Medium  | S      | Через свой сервер или без (single-device MVP) |
| P3  | Daily activity digest (для stand-up)                             | Low-Med | S      | Решает боль #7, генерируется локально         |

### Анти-фичи MVP

| Анти-фича                               | Почему нет                                               |
| --------------------------------------- | -------------------------------------------------------- |
| ❌ Write-back / ответы из inbox         | Расширяет scope PAT → бо́льшая поверхность атаки          |
| ❌ Облачное хранение токенов            | Главный страх пользователя. Токены только локально       |
| ❌ AI через внешний API (OpenAI и т.д.) | Отправка рабочих данных наружу — contra privacy-first    |
| ❌ 10+ интеграций сразу                 | Глубина важнее ширины. 5–6 идеальных > 12 сырых          |
| ❌ Team analytics / dashboards          | Другой ICP, другой продукт                               |
| ❌ Browser extension                    | Расширенный DOM-доступ нарушает security-first позицию   |
| ❌ Electron (в пользу Tauri)            | Electron: ~200 MB, Tauri: ~15 MB — важно для self-hosted |

---

## 4. Метрики успеха

> Продукт self-hosted/open-source → метрики иные, чем у SaaS

### 30 дней — Validation Metrics

| Метрика                                       | Цель           | Инструмент                             |
| --------------------------------------------- | -------------- | -------------------------------------- |
| GitHub stars                                  | ≥ 200          | GitHub Insights                        |
| Docker Hub pulls                              | ≥ 500          | Docker Hub stats                       |
| Activated installs (≥2 интеграции подключены) | ≥ 40% от pulls | Opt-in телеметрия / GitHub Discussions |
| Setup time (fork → первое уведомление)        | < 5 мин        | User testing (5 человек)               |
| Issues opened (bug vs feature request ratio)  | < 30% bugs     | GitHub Issues                          |
| Discord/Telegram community joins              | ≥ 100          | Community stats                        |

### 90 дней — Retention & Monetization Signals

| Метрика                                         | Цель            | Инструмент      |
| ----------------------------------------------- | --------------- | --------------- |
| GitHub stars                                    | ≥ 1 000         | GitHub Insights |
| Active installs (weekly pull от Docker)         | ≥ 300           | Docker Hub      |
| Sponsor / donation conversion (GitHub Sponsors) | ≥ 1–2% активных | GitHub Sponsors |
| Community contributors (PRs от не-авторов)      | ≥ 5             | GitHub          |
| Cloud-hosted waitlist signups                   | ≥ 150           | Лендинг + форма |
| NPS (Discord/Telegram опрос)                    | ≥ 45            | Manual survey   |

---

## 5. Роадмап — 3 Волны

### Wave 1 — Foundation (Месяцы 1–3)

**Тема: "Your notifications. Your machine. Your rules."**

| #     | Фича                                                       | Цель                    |
| ----- | ---------------------------------------------------------- | ----------------------- |
| W1-01 | PAT-интеграции: GitHub, GitLab, Telegram Bot, Linear, Jira | Сразу работает у 90% ЦА |
| W1-02 | Read-only агрегация → локальный SQLite                     | Local-first периметр    |
| W1-03 | Smart deduplication                                        | Убиваем боль #2         |
| W1-04 | Priority classifier (rule-based)                           | Signal vs noise         |
| W1-05 | Thread context stitching (issue ↔ PR ↔ alert)              | Главный дифференциатор  |
| W1-06 | Focus Mode / DND                                           | Deep work               |
| W1-07 | Keyboard navigation + command palette                      | Developer UX            |
| W1-08 | Docker Compose packaging + Web UI (Next.js)                | Установка за 2 минуты   |

**Стек:** Python FastAPI · Next.js · SQLite · Docker Compose  
**Exit criteria:** 200 GitHub stars · 500 Docker pulls · setup < 5 мин на cold test

---

### Wave 2 — Intelligence (Месяцы 4–6)

**Тема: "Smart, still local"**

| #     | Фича                                                     | Цель                                  |
| ----- | -------------------------------------------------------- | ------------------------------------- |
| W2-01 | Discord Bot интеграция                                   | Закрываем Discord-аудиторию           |
| W2-02 | Slack (только свой workspace через Bot Token)            | Частичное покрытие                    |
| W2-03 | Local AI classifier (Ollama / llama.cpp)                 | Умная приоритизация без утечки данных |
| W2-04 | Activity digest: локальный auto stand-up                 | Saves 10 min/day                      |
| W2-05 | Custom rules v2 (regex + advanced filters)               | Power user retention                  |
| W2-06 | Snooze + defer + reminders                               | Workflow completion                   |
| W2-07 | Tauri Desktop App (замена Electron-обёртки)              | Native, 15 MB vs 200 MB               |
| W2-08 | Optional cloud sync (self-hosted backend, E2E encrypted) | Multi-device без vendor               |

**Exit criteria:** 1 000 stars · 300 active installs · cloud waitlist ≥ 150

---

### Wave 3 — Monetization (Месяцы 7–12)

**Тема: "Free forever self-hosted. Pay for convenience."**

| #     | Фича                                                 | Бизнес-цель                            |
| ----- | ---------------------------------------------------- | -------------------------------------- |
| W3-01 | Cloud-hosted SaaS (managed, E2E encrypted)           | Монетизация без потери privacy-позиции |
| W3-02 | Teams: shared inbox + shared rules                   | Расширение от 1 к команде              |
| W3-03 | Teams, Zoom, PagerDuty (по demand из issues)         | Enterprise coverage                    |
| W3-04 | Universal search v2 (semantic, локальный embeddings) | Power UX                               |
| W3-05 | Mobile app (React Native + локальный сервер)         | On-call coverage                       |
| W3-06 | Plugin API для кастомных источников                  | Community integrations                 |
| W3-07 | GitHub Marketplace / VS Code extension               | Distribution channel                   |

**Монетизация Wave 3:**

- Self-hosted: бесплатно навсегда (open core)
- Cloud-hosted: $8–15/мес solo · $12–20/мес/seat team
- Enterprise self-hosted: $500–2000/мес (SLA + support)

**Exit criteria:** $10k MRR · 2 000+ GitHub stars · 5 community plugins

---

## Архитектурный скелет

```
unified-inbox/
├── docker-compose.yml          # одна команда — всё запускает
├── backend/
│   ├── main.py                 # FastAPI
│   ├── connectors/
│   │   ├── github.py           # PAT polling / webhooks
│   │   ├── gitlab.py
│   │   ├── telegram.py         # Bot API long polling
│   │   ├── linear.py
│   │   └── jira.py
│   ├── services/
│   │   ├── deduplication.py    # хэш-based event matching
│   │   ├── classifier.py       # rule-based приоритет
│   │   └── stitcher.py         # context linking
│   └── db/
│       └── local.db            # SQLite, никаких внешних зависимостей
└── frontend/
    └── ...                     # Next.js
```

---

## Ключевые риски (обновлено)

| Риск                                              | Вероятность | Митигация                                                 |
| ------------------------------------------------- | ----------- | --------------------------------------------------------- |
| GitHub/GitLab меняют rate limits                  | Средняя     | Webhook-first, polling как fallback                       |
| Пользователи не доверяют даже локальному хранению | Низкая      | Open source = аудит кода, никакой телеметрии по умолчанию |
| Трудно монетизировать self-hosted                 | Высокая     | Cloud tier с Day 1 как waitlist; open core модель         |
| Сложность поддержки 6+ коннекторов                | Средняя     | Plugin архитектура с Wave 2, community берёт нишевые      |

### Шаг 2: Security Architect

Промпт:

Ты senior security architect. Подготовь security blueprint для unified inbox.

Требования:

- Zero-trust между сервисами.
- Шифрование данных in-transit и at-rest.
- Клиент-ориентированная приватность (local-first где возможно).
- Безопасное хранение OAuth токенов и секретов.
- Полный аудит действий пользователя и администратора.

Сделай:

1. Threat model по STRIDE (активы, угрозы, векторы).
2. Data flow (текстовая диаграмма).
3. Security controls по слоям: client, backend, storage, network, ops.
4. Security baseline с приоритетами P0/P1/P2.
5. Чеклист "Go/No-Go" перед релизом.
6. Incident response и backup/disaster recovery policy.

Формат:

- Таблица + чеклист.
- Для каждого пункта: риск, контроль, критерий готовности.

#### Ответ агента (вставь сюда)

Каноничный источник для шага 2:
[docs/agent-answers/incoming/security-blueprint-unified-inbox.md](docs/agent-answers/incoming/security-blueprint-unified-inbox.md)

🔐 Security Blueprint: Unified Inbox

Версия: 1.0 | Классификация: INTERNAL | Дата: 2026-06-24
Цикл пересмотра: Ежеквартально | Статус: DRAFT → требует Security Lead review

0. Document Metadata

ПолеЗначениеОбласть примененияUnified Inbox (Multi-provider message aggregation)СтандартыOWASP Top 10, STRIDE, NIST SP 800-53, GDPR Art. 25/32Ключевые провайдерыGmail, Outlook, Slack, Telegram (OAuth 2.0 + PKCE)СредаCloud-native, multi-tenant, Zero-TrustСледующий пересмотр2026-09-24

1. STRIDE Threat Model

1.1 Реестр Критических Активов

IDАктивКлассификацияКомпонентКонф-тьЦелостностьДоступностьA-01OAuth access / refresh токены🔴 CRITICALToken VaultHIGHHIGHHIGHA-02Содержимое сообщений🔴 CONFIDENTIALMessage StoreHIGHMEDIUMMEDIUMA-03Ключи шифрования DEK/KEK🔴 CRITICALKMS / HSMCRITICALCRITICALHIGHA-04JWT сессионные токены🔴 CRITICALAuth ServiceHIGHHIGHHIGHA-05Метаданные сообщений🟡 SENSITIVEMessage StoreMEDIUMLOWLOWA-06Аудит-лог🔴 CONFIDENTIALAudit StoreMEDIUMCRITICALHIGHA-07PII пользователей🔴 PII/GDPRUser StoreHIGHMEDIUMLOWA-08API ключи внешних провайдеров🔴 CRITICALConfig StoreHIGHHIGHHIGHA-09TLS / mTLS сертификаты и ключи🔴 CRITICALPKICRITICALCRITICALCRITICALA-10Инфраструктурные секреты и конфиги🔴 CRITICALOps / VaultHIGHHIGHHIGH

DEK = Data Encryption Key (per-user, ежегодная ротация)
KEK = Key Encryption Key (per-tenant, 90-дневная ротация)

1.2 STRIDE Матрица Угроз

IDКатегорияУгрозаАктивыВектор атакиВер-тьУщербРискМитигацияT-01SpoofingПодделка identity сервиса внутри кластераA-04, A-09Скомпрометированный сертификат, MITMMEDIUMCRITICAL🔴 HIGHmTLS + SPIFFE/SPIRET-02SpoofingКража OAuth токена → impersonation пользователяA-01XSS, phishing, утечка в logsHIGHCRITICAL🔴 CRITICALToken rotation, encrypted store, CSPT-03TamperingПодмена содержимого сообщений при транзитеA-02MITM, скомпрометированный проксиLOWHIGH🟡 MEDIUMTLS 1.3 everywhere, message signingT-04TamperingМодификация / удаление аудит-логаA-06Инсайдер, скомпрометированная БДLOWCRITICAL🔴 HIGHAppend-only, WORM, HMAC chainT-05TamperingSQL/NoSQL инъекция через APIA-02, A-07Вредоносный пользовательский вводMEDIUMHIGH🔴 HIGHParameterized queries, WAF, ORMT-06RepudiationОтрицание факта действия пользователемA-06Отсутствие или повреждение логовMEDIUMMEDIUM🟡 MEDIUMИммутабельный audit log, цифровые подписиT-07Info DisclosureУтечка токенов через URL / query params / logsA-01, A-04HTTP log scraping, Referer headerHIGHCRITICAL🔴 CRITICALTokens only in headers/body, log sanitizationT-08Info DisclosureVerbose error messages → утечка PII / stack traceA-07Любой API endpointHIGHHIGH🔴 HIGHGeneric errors в prod, sanitized loggingT-09Info DisclosureУтечка KEK → расшифровка всей базыA-03Скомпрометированный KMS, инсайдерLOWCRITICAL🔴 HIGHHSM, envelope encryption, key rotationT-10Info DisclosureНарушение tenant isolation (IDOR)A-02, A-07Прямой перебор resource IDsMEDIUMCRITICAL🔴 HIGHRow-level security, tenant ID binding в JWTT-11Denial of ServiceToken endpoint flooding / credential stuffingA-01, A-04Brute-force, botnetsHIGHHIGH🔴 HIGHRate limiting, CAPTCHA, account lockoutT-12Denial of ServiceWebhook / message sync overloadA-02Вредоносный payload, webhook floodMEDIUMMEDIUM🟡 MEDIUMPayload limits, async queue, circuit breakerT-13EoPГоризонтальное перемещение между tenant'амиA-01, A-02IDOR + broken tenancy checkMEDIUMCRITICAL🔴 HIGHTenant ID в каждом запросе, RLS в БДT-14EoPAdmin account takeoverA-10Phishing, слабые credentialsMEDIUMCRITICAL🔴 HIGHMFA обязателен, PAM, JIT accessT-15EoPJWT claims manipulation (alg:none / HS256)A-04Алгоритм none атакаLOWCRITICAL🔴 HIGHRS256 only, strict alg validation, reject none

1.3 Векторы Атак (Simplified Kill Chain)

ФазаТехникаЦелевой активИндикатор (IOC)Initial AccessOAuth phishing → token theftA-01Логин из нетипичной геолокации/устройстваInitial AccessXSS → session hijackingA-04CSP violation report в SIEMExecutionMalicious webhook payload (RCE attempt)BackendOversized/malformed Content-TypePersistenceRefresh token abuse после ревокацииA-01Использование токена после logoutLateral MovementIDOR между tenant'амиA-02, A-07tenant_id mismatch в запросе / 403 spikeExfiltrationBulk export через API пагинациюA-02Аномально большой объём выгрузки за сессиюImpactUnauthorised KMS key operationA-03Попытка удаления/деактивации keyImpactTruncate / DELETE аудит-логаA-06DDL-команда на audit-таблице

2. Data Flow

2.1 Архитектурный Data Flow (Zero-Trust)

┌───────────────────────────────────────────────────────────────────────┐
│ UNIFIED INBOX — ZERO-TRUST DATA FLOW │
└───────────────────────────────────────────────────────────────────────┘

┌────────────────────┐
│ CLIENT │ Browser / Mobile App
│ ┌──────────────┐ │ → CSP, HSTS, Certificate Pinning (mobile)
│ │ Local Cache │ │ → IndexedDB / Keychain: AES-256-GCM
│ │ (AES-256) │ │ → JWT: memory ONLY (no localStorage)
│ └──────────────┘ │ → Auto-logout at 15 min idle
└────────┬────────────┘
│ TLS 1.3 + HSTS
▼
┌────────────────────────────────────────────┐
│ EDGE / CDN │
│ Cloudflare · WAF (OWASP CRS) │
│ DDoS Protection · Bot Management │
│ IP Reputation · Rate Limit (global) │
└─────────────────┬──────────────────────────┘
│ TLS 1.3
▼
┌────────────────────────────────────────────┐
│ API GATEWAY │
│ JWT Verify · Per-user Rate Limit │
│ CORS Whitelist · Request Schema Validation │
│ Tenant ID Injection from JWT claims │
└────────┬───────────────┬────────────────────┘
│ mTLS │ mTLS
▼ ▼
┌──────────────┐ ┌───────────────────────────────────────┐
│ AUTH │ │ MESSAGE SERVICE │
│ SERVICE │ │ Router · Normalizer · Encrypt Layer │
│ JWT + OAuth │ └───────┬────────────────┬──────────────┘
│ PKCE Flow │ │ mTLS │ mTLS
└──────┬───────┘ ▼ ▼
│ mTLS ┌─────────────────┐ ┌───────────────────┐
▼ │ PROVIDER │ │ MESSAGE QUEUE │
┌─────────────┐ │ CONNECTORS │ │ Kafka / RabbitMQ │
│ TOKEN │ │ ┌────────────┐ │ │ Encrypted at-rest │
│ VAULT │ │ │Gmail/OAuth │ │ └────────┬──────────┘
│ HashiCorp │ │ ├────────────┤ │ │
│ Vault+HSM │ │ │Outlook/O365│ │ ▼
└─────────────┘ │ ├────────────┤ │ ┌────────────────────┐
│ │Slack/Tg │ │ │ MESSAGE STORE │
│ └────────────┘ │ │ PostgreSQL │
└─────────────────┘ │ AES-256-GCM (field) │
│ Row-Level Security │
└────────┬─────────────┘
┌─────────────────────────────────────────│──────────┐
│ mTLS │ │
▼ ▼ ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ ADMIN SVC │ │ KMS │ │ AUDIT STORE │
│ RBAC + MFA │ │ Envelope Enc │ │ Append-Only │
│ PAM, JIT │ │ DEK→KEK→HSM │ │ HMAC Chain │
└──────────────┘ └──────────────┘ │ WORM/S3 Lock│
└──────────────┘

ЛЕГЕНДА:
─────── TLS 1.3 (внешний трафик)
═══════ mTLS (внутренний zero-trust, SPIFFE SVID identity)
DEK Data Encryption Key — per user
KEK Key Encryption Key — per tenant, managed by KMS
HSM Hardware Security Module — master key never leaves HSM

2.2 OAuth 2.0 + PKCE Token Flow

Пользователь API Gateway Auth Service Token Vault Provider
│ │ │ │ │
│─ Connect ──────▶ │ │ │
│ │─ Forward ──────▶ │ │
│ │ │─ Gen PKCE ─ │ │
│ │ │ code_verifier│ │
│ │ │ code_challenge (S256) │
│◀─── Redirect to Provider OAuth ────────────────────────────────│
│─ User grants permissions ────────────────────────────────────▶ │
│◀─── auth_code + state ─────────────────────────────────────── │
│─ auth_code ────▶ │ │ │
│ │─ Verify state ▶ │ │
│ │ │─ Exchange code + verifier ──▶│
│ │ │◀── access_token + refresh ───│
│ │ │─ Encrypt ────▶│ │
│ │ │ & store token│ │
│◀─ 200 OK ──────│◀─ Success ─────│ │ │

⚠️ ПРАВИЛА ТОКЕНОВ:

1. code_verifier НИКОГДА не передаётся по сети (PKCE S256)
2. access_token НИКОГДА не хранится на клиенте
3. Vault хранит только зашифрованные токены (AES-256)
4. Refresh rotation: каждый use → новый refresh_token (старый инвалидируется)
5. state parameter проверяется (CSRF protection)
6. Token binding к User-Agent + IP (soft check, alert on mismatch)

7. Security Controls по Слоям

3.1 Client Layer

IDКонтрольУгрозаРеализацияКритерий готовностиCL-01Content Security Policy (CSP)T-02 XSSdefault-src 'self'; no unsafe-inline; report-uri активенGrade A на securityheaders.com; 0 violations в prodCL-02JWT только в памяти (не в localStorage)T-02, T-07Token в JS closure / httpOnly Secure cookie; sessionStorage запрещёнPentest не обнаруживает токен через storage APICL-03HTTPS Strict + HSTS PreloadT-03 MITMStrict-Transport-Security: max-age=31536000; includeSubDomains; preloadДомен включён в HSTS preload listCL-04Certificate Pinning (mobile)T-01, T-03iOS: TrustKit; Android: OkHttp network security configБлокирует подмену сертификата в тестеCL-05Локальное шифрование кэшаT-09 PhysicalAES-256-GCM через WebCrypto API / iOS Keychain / Android KeystoreДанные нечитаемы без device unlockCL-06Auto-logout при бездействииT-02 Session15 мин idle → token revoke + clear memoryПодтверждено функциональным тестомCL-07DOMPurify sanitization HTML emailT-05 XSSDOMPurify для рендеринга HTML-содержимого писемOWASP ZAP scan: 0 XSS findingsCL-08Subresource Integrity (SRI)Supply chainintegrity="sha384-..." на все CDN/external ресурсыВсе external scripts имеют SRI hash

3.2 Backend Layer

IDКонтрольУгрозаРеализацияКритерий готовностиBE-01JWT RS256; строгая валидация algT-15 EoPRS256 only; reject alg:none, HS256; проверка exp, iss, audТест: alg:none → 401; истёкший → 401BE-02Refresh Token Rotation + theft detectionT-02Каждый use инвалидирует старый токен; reuse → revoke all sessionsПовторное использование old token → revoke + alertBE-03Rate Limiting per user + per IPT-11 DoSAuth: 5 req/min; API: 100 req/min; lockout после 10 failedRate limit срабатывает в нагрузочном тестеBE-04Input Validation (schema-based, whitelist)T-05 InjectZod/Joi/Pydantic на каждый endpoint; reject unexpected fieldsFuzz test не вызывает 500 ошибокBE-05Tenant Isolation: tenantId из JWT, не requestT-10, T-13tenantId извлекается ТОЛЬКО из JWT claims; RLS на уровне БДPentest: нет IDOR между tenant'амиBE-06Нет hardcoded secrets (Vault everywhere)T-01HashiCorp Vault dynamic secrets; env vars только для Vault addrgitleaks detect: 0 findings в git historyBE-07Dependency scanning в CI (SCA)Supply chainSnyk/Dependabot; pipeline block на Critical CVECI fails при Critical CVE в зависимостяхBE-08CORS Whitelist; no wildcard в prodT-02 CSRFСписок разрешённых origins; credentials: true только для своих доменовConfig review: нет \* в prod CORSBE-09Sanitized error responsesT-08 DisclosureProd: generic error + error_id; stack trace только во внутренних logsPentest: нет PII / stack trace в 4xx/5xxBE-10Message payload size limitsT-12 DoSAttachment max 50MB; request body max 1MBOversized request → 413 немедленно; no OOM

3.3 Storage Layer

IDКонтрольУгрозаРеализацияКритерий готовностиST-01Шифрование at-rest: Envelope EncryptionT-09AES-256-GCM; DEK per user → KEK per tenant (KMS) → Master Key (HSM)Прямой запрос к диску/файлам: только ciphertextST-02Field-level encryption для PII и bodyT-09, T-10message_body, subject, from_address, to_address — encrypted columnsSELECT в БД: encrypted columns возвращают ciphertextST-03Row-Level Security (PostgreSQL RLS)T-10, T-13SET app.current_tenant_id = $1 + RLS policy на каждой таблицеUser из tenant A не видит данные tenant BST-04Отдельный DB user per сервис (least priv)T-04, T-13message_svc: SELECT+INSERT; admin_svc: +UPDATE; audit_svc: INSERT onlyDB credentials per service в VaultST-05Append-only Audit Log (HMAC chain)T-04, T-06Отдельная БД; INSERT-only роль; HMAC на каждой строке; chain validationUPDATE/DELETE на audit таблице → permission deniedST-06WORM backup для Audit StoreT-04 TamperS3 Object Lock (Compliance mode) / Azure Immutable Blob StorageПопытка удалить audit backup → errorST-07Шифрование резервных копийT-09pgBackRest с AES-256; ключи бэкапов хранятся отдельно от данныхБэкап без ключа нерасшифруемST-08Automated Key Rotation PolicyT-09DEK: ежегодно; KEK: 90 дней; автоматическая re-encryption при ротацииRotation job: 0 downtime; валидация после ротации

3.4 Network Layer

IDКонтрольУгрозаРеализацияКритерий готовностиNW-01TLS 1.3 на всех внешних endpointsT-03 MITMMin TLS 1.2 (deprecated 2027); TLS 1.0/1.1 disabled; ECDHE cipher onlytestssl.sh: A+ рейтинг; no weak ciphersNW-02mTLS между всеми internal сервисамиT-01, T-03Istio / Linkerd service mesh; SPIFFE SVID как crypto identityТрафик без valid cert → connection refusedNW-03Network Segmentation (VPC/Subnet)T-13Prod/Staging/Dev в отдельных VPC; DB в private subnet (no public IP)Nmap: DB endpoint недоступен из internetNW-04WAF (Web Application Firewall)T-05, T-11OWASP Core Rule Set (CRS); custom rules для OAuth endpointsWAF блокирует SQLi/XSS/path traversal в тестеNW-05DDoS Protection (L3/L4/L7)T-11, T-12Cloudflare / AWS Shield Advanced; adaptive rate limiting на edgeDDoS симуляция: availability не нарушенаNW-06Zero-Trust Network Access (ZTNA) для adminT-14Infra admin доступ только через ZTNA + MFA; no SSH from internetSSH/RDP без ZTNA клиента недоступныNW-07Egress Filtering (outbound whitelist)ExfiltrationWhitelist провайдеров (Google/Microsoft/Slack API hostnames); block unexpectedOutbound трафик только к approved API endpointsNW-08DNS Security (DNSSEC)T-01, T-03DNSSEC на домене; DNS-over-HTTPS для internal resolutionDNSSEC validation активен; dig +dnssec → AD flag

3.5 Ops Layer

IDКонтрольУгрозаРеализацияКритерий готовностиOP-01SIEM + IOC AlertingВсеELK/Splunk; алерты по §1.3 IOC; MTTR target < 15 min (SEV-1)Тестовый алерт срабатывает < 5 minOP-02MFA обязателен для всех adminT-14TOTP / FIDO2 / hardware key; bypass MFA = невозможно в prodAudit: 100% admin аккаунтов с MFAOP-03Least Privilege + Just-In-Time accessT-14RBAC; PAM (Teleport/BeyondTrust); 0 standing admin privilegesJIT session audit: доступ выдаётся на время задачиOP-04CI/CD Security GatesSupply chainSAST (Semgrep), DAST (OWASP ZAP), SCA (Snyk) в pipelinePipeline fail при HIGH+ уязвимостиOP-05Secrets scanning в git (pre-commit + CI)T-01gitleaks + git-secrets pre-commit hook; также в CI pipelinegitleaks detect: 0 findingsOP-06Vulnerability Management SLAВсеCritical: patch 24h; High: 72h; Medium: 7 днейSLA соблюдается в 95%+ случаев (tracked)OP-07Quarterly Penetration TestingВсеExternal WAPT + internal red team; scope: OAuth flows, IDOR, authPentest report: 0 Critical/High открытых findingsOP-08Immutable Infrastructure + Image SigningSupply chainContainer images подписаны (Cosign/Notary); no SSH в prod podskubectl exec / SSH в prod → запрещено policyOP-09Log retention + immutabilityT-04, T-06Logs shipped to immutable store; 1 год minimum; no app-level deleteLogs нельзя удалить через app credentialsOP-10SBOM generation (Software Bill of Materials)Supply chainCycloneDX SBOM при каждом build; хранится с release артефактамиSBOM актуален и доступен для каждого release

4. Security Baseline — Приоритеты P0 / P1 / P2

ПриоритетIDКонтрольУгрозаКритерий готовностиДедлайн🔴 P0BE-01JWT RS256 + строгая валидация algT-15 CRITICAL EoPalg:none → 401; тест автоматизированДо первого деплоя🔴 P0BE-05Tenant isolation (JWT + RLS)T-10, T-13 CRITICALPentest: нет IDOR между tenant'амиДо первого деплоя🔴 P0ST-01Шифрование at-rest AES-256 (envelope)T-09 CRITICALSELECT в БД: ciphertext, не plaintextДо первого деплоя🔴 P0NW-01TLS 1.3 everywhere (external)T-03testssl.sh A+; TLS 1.0/1.1 disabledДо первого деплоя🔴 P0CL-01Content Security Policy (CSP)T-02 CRITICALGrade A; 0 violations в prodДо первого деплоя🔴 P0BE-06Нет hardcoded secrets (Vault)T-01 CRITICALgitleaks: 0 findings в git historyДо первого деплоя🔴 P0CL-03HSTS PreloadT-03Включён в preload list; max-age=31536000До первого деплоя🔴 P0OP-02MFA для всех admin аккаунтовT-14 CRITICALAudit: 100% admin с MFAДо первого деплоя🔴 P0ST-05Append-only Audit LogT-04, T-06DELETE → permission denied (тест)До первого деплоя🔴 P0BE-03Rate Limiting auth endpointsT-11Брутфорс заблокирован в нагрузочном тестеДо первого деплоя🟠 P1NW-02mTLS между всеми сервисамиT-01, T-03Весь inter-service трафик mTLSSprint +1🟠 P1BE-02Refresh Token Rotation + theft detectionT-02 CRITICALReuse → revoke all sessions + alertSprint +1🟠 P1ST-02Field-level encryption PIIT-09PII columns: encrypted в БДSprint +1🟠 P1NW-04WAF (OWASP CRS)T-05, T-11WAF активен; SQLi тест блокированSprint +1🟠 P1OP-04CI/CD security gates (SAST/SCA)Supply chainPipeline fail на HIGH CVESprint +1🟠 P1BE-09Sanitized error responsesT-08Нет PII / stack trace в prod ошибкахSprint +1🟠 P1ST-03Row-Level Security PostgreSQLT-10, T-13RLS policy активна на всех таблицахSprint +1🟠 P1OP-01SIEM + IOC AlertingВсеТестовый алерт: < 5 minSprint +2🟠 P1NW-03Network Segmentation (VPC)T-13DB subnet изолирован; no public IPSprint +1🟠 P1CL-07DOMPurify sanitization HTML emailT-05 XSSZAP scan: 0 XSS findingsSprint +1🟡 P2OP-07Quarterly Pentest (external WAPT)Все1й pentest: 0 Critical/High open3 мес после релиза🟡 P2CL-04Certificate Pinning (mobile)T-01, T-03Blocking при подмене cert в тестеSprint +3🟡 P2ST-08Automated Key RotationT-09DEK/KEK ротация без downtime1 мес после релиза🟡 P2OP-08Immutable Infrastructure + CosignSupply chainSSH в prod pod: запрещеноSprint +3🟡 P2NW-07Egress Filtering (whitelist)ExfiltrationOutbound только к approved endpointsSprint +3🟡 P2OP-10SBOM generation (CycloneDX)Supply chainSBOM в каждом releaseSprint +3🟡 P2NW-08DNSSECT-01, T-03DNSSEC validation активен2 мес после релиза🟡 P2OP-03JIT admin access (PAM)T-140 standing admin privSprint +4

5. Go / No-Go Checklist (Pre-Release)

✅ GO: все чекбоксы отмечены
🚫 NO-GO: любой пункт 1–21 не выполнен — деплой заблокирован

🔐 Аутентификация и Авторизация

#ПроверкаРискКритерий GO✓1JWT использует RS256; alg:none отклонёнT-15 CRITICALАвтотест: alg:none → 401☐2Access token: expiry 15 мин; хранится только в памятиT-02, T-07Pentest: токен не найден в localStorage/cookie☐3Refresh token rotation при каждом useT-02Тест: старый refresh после use → 401☐4MFA обязателен для всех admin аккаунтовT-14Audit: 0 admin без MFA☐5OAuth PKCE (S256) реализованT-02Обмен кода без code_verifier → rejected☐

🏢 Multi-Tenancy и Изоляция

#ПроверкаРискКритерий GO✓6tenantId берётся из JWT claims, НЕ из request bodyT-13 CRITICALCode review подтверждён + тест☐7PostgreSQL RLS включён на всех таблицахT-10, T-13Тест: User-A не видит данные User-B☐8IDOR scan пройден (automated или pentest)T-10Automated IDOR scan: 0 findings☐

🔑 Секреты и Шифрование

#ПроверкаРискКритерий GO✓90 hardcoded secrets в git (gitleaks scan)T-01, T-09 CRITICALgitleaks detect: 0 findings☐10Все секреты через HashiCorp VaultT-01Env vars: только Vault addr + app_role ID☐11Данные в БД зашифрованы at-rest (AES-256)T-09Прямой SELECT в БД → ciphertext☐12PII-поля зашифрованы на уровне columnT-09Audit PII columns: все encrypted☐

🌐 Сеть и Транспорт

#ПроверкаРискКритерий GO✓13TLS 1.3 на всех внешних эндпоинтахT-03testssl.sh: A+; TLS 1.0/1.1 disabled☐14HSTS включён (+ preload)T-03Header присутствует; max-age=31536000; preload☐15WAF активен (OWASP CRS)T-05, T-11WAF тест: SQLi и XSS векторы заблокированы☐16DB в изолированной подсети (no public IP)T-13Nmap: DB endpoint недостижим из internet☐17CORS: нет \* в prod конфигурацииT-02Config review: whitelist origins only☐

📋 Аудит и Логирование

#ПроверкаРискКритерий GO✓18Audit log append-only (DELETE → forbidden)T-04, T-06Тест: DELETE на audit table → permission denied☐19Логи не содержат токены / пароли / PIIT-07 CRITICALLog sampling: 0 sensitive values в logs☐20SIEM алерты настроены (критические IOC из §1.3)ВсеTest alert: срабатывает < 5 min☐21Log retention ≥ 1 год (GDPR compliance)T-06Logs archived с immutable storage☐

🏗️ CI/CD и Supply Chain

#ПроверкаРискКритерий GO✓22SAST (Semgrep) в pipeline; блокирует HIGH+Supply chainPipeline: 0 пропущенных HIGH findings☐23SCA (Snyk) блокирует Critical CVESupply chainНет known Critical CVE в зависимостях☐24Dependency lock files в VCSSupply chainpackage-lock.json / poetry.lock актуальны☐

🚨 Incident Readiness

#ПроверкаРискКритерий GO✓25IR Runbook задокументирован и доступен on-callВсеRunbook в wiki; команда ознакомлена☐26Token revocation endpoint работает корректноT-02Тест: revoke → следующий request → 401☐27Backup restore тест пройден (RTO < 4h)DRFull restore: завершён за < RTO☐28On-call ротация настроена (PagerDuty/OpsGenie)ВсеТест алерт: on-call получает notification☐29GDPR Data Processing Agreement актуаленGDPR/LegalLegal review: approved; DPA подписан☐

6. Incident Response Policy

6.1 Severity Matrix

SeverityОписаниеПримерыNotify SLAContain SLA🔴 SEV-1Критический: данные под угрозойOAuth token leak, tenant isolation breach, KMS compromise< 15 min< 1 hr🟠 SEV-2Серьёзный: частичная компрометацияAdmin account takeover, audit log tampering attempt, массовые failed logins< 30 min< 4 hr🟡 SEV-3Подозрительная активность, ущерба нетАномальный трафик, необычная геолокация, rate limit abuse< 1 hr< 8 hr⚪ SEV-4ИнформационныйУязвимость в зависимости (Medium), failed logins ниже порога< 24 hr< 72 hr

6.2 IR Phases (NIST SP 800-61)

ФазаДействияОтветственныйИнструменты1. DetectSIEM alert / user report; подтверждение severityOn-call engineerSIEM, PagerDuty/OpsGenie2. TriageОпределить scope: какие активы и пользователи затронуты; собрать доказательстваSecurity LeadKibana/Splunk, audit logs3. ContainRevoke tokens; block malicious IP; isolate affected tenant; disable compromised accountDevOps + SecurityVault CLI, WAF, K8s NetworkPolicy4. EradicateУдалить вектор: патч, ротация ключей, удаление злоумышленникаDev + SecurityPatch pipeline, KMS rotate5. RecoverВосстановление: restore from backup, re-enable с новыми credentialsDevOpsDR runbook, pgBackRest6. Post-IncidentRCA; обновление runbook; GDPR notification если требуется; lessons learnedAllConfluence/Notion

6.3 GDPR / Регуляторные Уведомления

СитуацияДействиеДедлайнПодтверждённая утечка PIIУведомить DPA (UODO в Польше)< 72 часаУтечка PII > 250 пользователейУведомить DPA + уведомление пользователям< 72 часаOAuth token leakУведомить затронутых пользователей< 24 часаKMS / ключи компрометированыEmergency re-encryption + notify регулятораНемедленноAdmin account compromiseInternal notify + audit все действия аккаунта< 1 hr

6.4 Сценарии Containment (Quick Reference)

СценарийШаги containmentVault команда / ActionOAuth token leakRevoke все токены пользователяvault lease revoke -prefix auth/oauth/user/{id}Mass token compromiseKill-switch: revoke все OAuth tokensvault lease revoke -prefix auth/oauth/Compromised service accountRotate Vault approle secret_idvault write -f auth/approle/role/{svc}/secret-idActive intrusion (lateral movement)Isolate pod / kill sessionskubectl delete pod {pod} + WAF IP blockAudit log tampering attemptAlert + lock audit DB accessRevoke audit DB user session

7. Backup & Disaster Recovery Policy

7.1 RPO / RTO Targets

КомпонентRPO (макс. потеря данных)RTO (макс. время восстановления)СтратегияMessage Store (PostgreSQL)1 час4 часаWAL streaming → S3; daily full backupToken Vault (HashiCorp)0 (HA cluster)30 минRaft consensus; multi-AZ auto-failoverAudit Store0 (append + replication)1 часStreaming replica + WORM S3 backupKMS / HSM0 (HA HSM cluster)15 минHSM cluster; key escrow в sealed envelopeMessage Queue (Kafka)15 мин2 часаReplication factor 3; topic S3 offload

7.2 Backup Schedule & Policy

КомпонентЧастотаТипШифрованиеRetentionХранилищеPostgreSQLWAL streaming (непрерывно) + daily fullIncremental + FullAES-256 (отдельный key)30 дней daily; 1 год weeklyS3 (отдельный аккаунт)Audit StoreReal-time реплика + daily fullFullAES-2567 лет (GDPR Art. 17)S3 Object Lock (Compliance)Vault snapshotsDailyFullVault native seal90 днейS3 (отдельный аккаунт)Config / SecretsПри каждом измененииVersion-controlledVault transit encryption1 годVault + git (encrypted refs)Kafka topicsContinuous replicationStreamingKafka at-rest AES-2567 дней hot; S3 offload 1 годIn-cluster + S3

7.3 Recovery Runbook (Scenarios)

СценарийШаги восстановленияRTO TargetОтветственныйDB Corruption1. Stop writes → 2. pgBackRest restore → 3. Apply WAL → 4. Validate → 5. Resume< 4 hrDBA + DevOpsKMS Compromise1. Rotate master key → 2. Re-encrypt все DEKs → 3. Revoke старые KEKs → 4. Audit logs< 2 hrSecurity + DBARegion Failure1. DNS failover → 2. Cross-region restore → 3. Validate integrity → 4. Monitor< 8 hrDevOpsOAuth Mass Leak1. Revoke все tokens (Vault) → 2. Force re-auth всех users → 3. Rotate client secrets → 4. Notify< 1 hrSecurity + DevOpsRansomware1. Isolate сеть → 2. Preserve evidence → 3. Restore immutable backup → 4. Notify DPA< 24 hrAll teams

7.4 DR Testing Schedule

ТестЧастотаКритерий успехаBackup restore (full PostgreSQL)ЕжемесячноRestore < RTO; данные консистентны после restoreAutomatic failover (primary DB → replica)ЕжеквартальноFailover < 60 сек; 0 data lossCross-region DR drillРаз в полгодаПолный сервис восстановлен < 8 hrIR tabletop exerciseЕжеквартальноКоманда знает роли; runbook актуаленKey rotation drillЕжемесячноRotation без downtime; 0 decryption errorsToken revocation mass testДо каждого major release100% tokens revoked < 60 сек

Appendix A: Security Contacts & Escalation Matrix

РольОтветственностьEscalationSecurity LeadIR coordination, threat model reviews, pentest→ CTOOn-Call DevOpsFirst responder, containment, infra→ Security LeadDBADB restore, key operations→ Security LeadLegal / DPOGDPR notification, DPA communications→ CEOProvider ContactOAuth issues with Gmail/Outlook/Slack APIsExternal support channels

Appendix B: Полезные Команды (Quick Reference)

bash# Проверка TLS
testssl.sh --full https://inbox.yourdomain.com

# Поиск secrets в git

gitleaks detect --source . --verbose

# Проверка CSP headers

curl -I https://inbox.yourdomain.com | grep -i content-security

# PostgreSQL: проверка RLS

SET app.current_tenant_id = 'tenant-A';
SELECT COUNT(\*) FROM messages; -- должно вернуть только messages tenant-A

# Vault: revoke токены пользователя

vault lease revoke -prefix auth/oauth/user/<user_id>

# Проверка mTLS (inter-service)

istioctl authn tls-check <pod-name> <service-name>

Статус: DRAFT | Следующий review: 2026-09-24 | Владелец: Security Architecture
Требует review от: Security Lead + Legal/DPO перед финализацией

### Шаг 3: API Integrations Architect

Промпт:

Ты solution architect по API-интеграциям. Нужна матрица интеграций для unified inbox.

Сервисы:
Slack, Discord, GitHub, GitLab, Jira, Linear, Rocket.Chat, Teams, Zoom, Google Calendar/Meet, Telegram, WhatsApp Business, Viber.

Сделай:

1. Какие события забирать (DM, mentions, PR comments, incidents, meetings и т.д.).
2. Модель получения: webhook / polling / websocket.
3. Нужные scopes/permissions.
4. Ограничения API/rate limits/квоты.
5. Сложность интеграции (Low/Med/High).
6. Риск по безопасности и комплаенсу.
7. Рекомендованный приоритет Wave 1/2/3.

Формат:

- Одна большая таблица.
- В конце: топ-8 интеграций для первого релиза.

#### Ответ агента (вставь сюда)

Каноничный источник для шага 3:
[docs/agent-answers/incoming/unified-inbox-integration-matrix.md](docs/agent-answers/incoming/unified-inbox-integration-matrix.md)

Unified inbox — integration matrix
Solution architecture · 13 services · Event retrieval, rate limits, security risk, wave prioritization

Model:
Webhook
WebSocket
Polling
Complexity:
Low
Med
High
Security risk:
● Low
● Low–Med
● Med
● High
Wave:
Wave 1
Wave 2
Wave 3
Filter:
All (13)
Wave 1 — 5 services
Wave 2 — 5 services
Wave 3 — 3 services

# Service Events Retrieval model Scopes / Permissions Rate limits / Quotas Complexity Security / Compliance Wave

1
Slack
DMs
@mentions
App mentions
Channel msgs
Reactions
Thread replies
Webhook (Events API)
WebSocket (Socket Mode)
channels:historyim:historygroups:historyapp_mentions:readusers:readreactions:read Tier 1: 1 req/min
Tier 4: 100+ req/min
Socket Mode: real-time
Web API: per-method Med ● Med risk
SOC2 T2 ✓ · GDPR ✓
Risk: DM data exposure,
workspace-wide scopes
Wave 1
2
GitHub
PR comments
Issue mentions
Review requests
CI/CD alerts
Release events
Workflow runs
Webhook
reponotificationsissuespull_requestsFine-grained PAT ✓ 5,000 req/hr (auth)
60 req/hr (anon)
Secondary limits apply
Webhook: real-time Low ● Low risk
SOC2 T2 ✓
Fine-grained tokens ✓
Code content not exposed
Lowest risk in list
Wave 1
3
GitLab
MR comments
Issue mentions
Pipeline events
CI/CD notif.
Notes / threads
Webhook
REST polling
read_apiread_userread_repository GitLab.com: 2,000/min
Self-hosted: configurable
Webhook: real-time
Pipeline events: unlimited Low ● Low–Med risk
SOC2 T2 (cloud) ✓
Self-hosted: TLS/auth
not guaranteed
Wave 1
4
Jira
Issue created/updated
Comments
Assignments
Status transitions
Sprint events
Epic changes
Webhook (Cloud)
REST polling (Server/DC)
read:jira-workread:jira-usermanage:jira-webhook Cloud: ~10,000 req/hr
Max 50 webhooks/project
Server/DC: no limit
Retry policy required Med ● Med risk
SOC2 · ISO27001 ✓
Server: HTTPS optional
Project data: sensitive
Wave 1
5
Google Cal / Meet
Event created/updated
Event cancelled
RSVP changes
Meet link gen.
Recurring events
Push (watch API)
REST polling
calendar.readonlycalendar.events.readonly 1M queries/day
500 req/100s per user
Watch TTL: 7 days
Renewal cron required! Med ● Low risk
SOC 1/2/3 · ISO27001 ✓
GDPR ✓
Watch channels expire:
cron renewal needed
Wave 1
6
Discord
DMs
Guild messages
Mentions
Thread msgs
Reactions
Voice events
WebSocket (Gateway)
Webhook (outgoing)
MESSAGE_CONTENT (priv!)GUILDSGUILD_MESSAGESDIRECT_MESSAGES 50 req/s (global)
5 req/5s per route
Gateway: 120 events/min
Privileged: verify >100 srv Med ● Med risk
MESSAGE_CONTENT: privileged

> 100 servers: verification
> Not GDPR-certified
> Discord ToS restrictions
> Wave 2
> 7
> Linear
> Issues created/updated
> Comments
> Cycle changes
> Project updates
> Assignments
> Priority changes
> Webhook
> GraphQL subscriptions
> read (OAuth 2.0)issues:create 1,500 req/hr (GraphQL)
> 400 complexity pts/query
> Webhook: real-time
> Best limits in the list Low ● Low risk
> SOC2 T2 ✓
> Modern OAuth2 ✓
> Minimal PII exposure
> Excellent docs
> Wave 2
> 8
> MS Teams
> DMs
> Channel mentions
> Meeting notif.
> Adaptive cards
> Presence changes
> Bot Framework
> Graph API webhooks
> Chat.ReadChannelMessage.Read.AllPresence.Read.AllCalendars.Read 4 req/s per app/tenant
> 3,000 req/10s per app
> Bot: 1,800 msg/min/app
> Graph: per-resource throttle High ● Low risk
> SOC1/2 · ISO27001 ✓
> HIPAA · FedRAMP ✓
> Requires Azure AD app +
> Bot Framework setup
> Wave 2
> 9
> Zoom
> Meeting start/end
> Participant join/leave
> Recording ready
> Webinar events
> Cloud recording
> Webhook (Event Subscriptions)
> meeting:read:adminwebinar:read:adminrecording:read 100 req/s (global)
> Some endpoints: 1 req/s
> Recording: 1 req/s
> Max 30 subscriptions/app Low ● Med risk
> SOC2 T2 ✓
> HIPAA addon available
> Risk: recording data access
> Limited audit trail
> Wave 2
> 10
> Telegram
> Bot DMs
> Group mentions
> Commands
> File shares
> Inline queries
> Poll results
> Webhook
> Long polling (getUpdates)
> Bot Token (no OAuth)Group admin rights 30 msg/s (global)
> 20 msg/min per chat
> getUpdates: 100 req/s
> Files: up to 50MB Low ● Med risk
> No E2E in groups
> UAE jurisdiction (risk)
> GDPR: gray area
> Not enterprise-certified
> Wave 2
> 11
> Rocket.Chat
> DMs
> Channel messages
> Mentions
> Room notif.
> File shares
> Integration events
> WebSocket (Realtime API)
> Webhook
> REST API
> API Key + User TokenRoom-level permissionsadmin (optional) Self-hosted: configurable
> Default: 200 req/min
> WebSocket: unlimited
> Version variability High ● High risk
> Self-hosted: TLS not guaranteed
> Auth varies by version
> SSO: complex config
> Audit trail: instance-dep.
> Wave 3
> 12
> WhatsApp Business
> Messages received
> Delivery/read status
> Template messages
> Media messages
> Button replies
> Webhook (Cloud API)
> whatsapp_business_messagingwhatsapp_business_managementMeta Business Verification Cloud API: 1,000 msg/s
> 250 recipients/batch
> Template: pre-approval req.
> Phone number tier limits High ● High risk
> Meta verification required
> GDPR EU: legal tension
> Business approval process
> Meta accesses metadata
> Wave 3
> 13
> Viber
> Messages
> Delivery/seen status
> Subscriber events
> Media messages
> Rich media cards
> Webhook
> Bot auth tokenPublic Account req.Partner approval needed 500 msg/s (Bot API)
> 30 msg/s per sender
> Public Account: higher
> Varies by region Med ● Med risk
> GDPR compliant ✓
> Limited enterprise use
> Partner approval required
> Few security audits
> Wave 3
> Top-8 integrations for first release
> Selected by: audience reach × integration complexity × dev-team value × security risk

1
Slack
Most widespread team chat. Mature Events API + Socket Mode. Maximum enterprise audience reach.
Wave 1
Med
2
GitHub
Essential for every dev team. Lowest complexity. Fine-grained PAT, minimal security risk.
Wave 1
Low
3
Jira
De facto enterprise PM standard. High ROI: issue event aggregation is core unified inbox value.
Wave 1
Med
4
GitLab
Direct analog to GitHub in complexity. Critical for teams with self-hosted CI/CD pipelines.
Wave 1
Low
5
Google Cal / Meet
Meetings-as-context: core inbox value. Push API + SOC 1/2/3. Wide corporate penetration.
Wave 1
Med
6
Linear
Fast-growing product/dev tool. Best GraphQL API in the list. Simple to integrate, minimal risk.
Wave 2
Low
7
Zoom
Meeting lifecycle without complex setup. Simple webhook. Wide enterprise market penetration.
Wave 2
Low
8
Telegram
Simplest auth model (Bot Token, no OAuth). Popular among dev teams for internal notifications.
Wave 2
Low

Несколько ключевых наблюдений по матрице:

Wave 1 — почему именно эти пять. GitHub и GitLab — простейшие в списке: один webhook, никакого WebSocket, минимальный security surface. Slack — самый высокий охват аудитории при зрелом API. Jira закрывает project tracking, который фигурирует в 90% use case unified inbox. Google Calendar даёт meeting context, без которого inbox выглядит неполным.

Главные технические риски по волнам:

Wave 2 — MS Teams сложнее всех в своей волне: нужна регистрация в Azure AD, Bot Framework, отдельный app registration в Portal. Discord требует верификации бота при росте выше 100 серверов — заложи это в роадмап заранее.

Wave 3 — WhatsApp Business блокирует старт из-за Meta Business Verification (процесс занимает 1–4 недели). Rocket.Chat — nightmare self-hosted variability: один клиент на v5, другой на v6, третий за корпоративным прокси без TLS. Viber практически не даёт ROI на европейском enterprise-рынке.

Три скрытых сложности, которые часто упускают:

Google Calendar watch channels истекают через 7 дней — нужен cron-renewal, иначе перестанешь получать события в production без единого error log.
Jira Cloud ограничивает 50 зарегистрированных webhooks на проект — при большом числе клиентов нужна мультиплексирующая прослойка.
Telegram Bot Token — удобно, но при интеграции в enterprise нужна отдельная политика ключей: один компрометированный токен = полный доступ к боту.
Рекомендованная последовательность Wave 1: GitHub → GitLab (одна кодовая база, минимальные различия) → Slack → Google Calendar → Jira (в конце, из-за Cloud/Server расхождения).

### Шаг 4: UX/IA Architect

Промпт:

Ты lead UX для productivity/security apps. Спроектируй UX и IA для unified inbox.

Нужны экраны:

- Onboarding
- Connect Source
- Unified Inbox
- Thread View
- Focus Mode
- Incident Mode
- Security Center

Сделай:

1. Пользовательские флоу (happy path + error path).
2. IA (навигация, структура экранов).
3. Правила приоритизации уведомлений.
4. Empty states и error states.
5. UX-принципы против перегрузки пользователя.

Формат:

- Пошаговые сценарии + wireframe-описания текстом.

#### Ответ агента (вставь сюда)

UX & IA Design Document — Unified Inbox

Role: Lead UX, Productivity & Security Apps
Version: 1.0

0. Продуктовый контекст

Продукт: Unified Inbox — единое рабочее пространство для сообщений из всех источников (email, мессенджеры, трекеры задач, CI/CD, security alerts) с приоритизацией, фокус-режимом и встроенным центром безопасности.

Целевая аудитория: Разработчики, DevOps, TeamLeads, Security-инженеры. Люди, у которых 5+ источников уведомлений и хроническая информационная перегрузка.

Ключевой принцип продукта: Inbox — это рабочий инструмент, а не задача на обработку. Пользователь не должен думать "что важно" — система делает это за него.

1. Information Architecture

1.1 Карта экранов

Unified Inbox App
│
├── Onboarding (однократно)
│ ├── Welcome
│ ├── Account Setup
│ ├── Connect First Source (≥1)
│ └── Tutorial Overlay
│
├── Core Shell (постоянная навигация)
│ ├── [L1] Unified Inbox ← точка входа по умолчанию
│ ├── [L1] Focus Mode ← временное состояние
│ ├── [L1] Incident Mode ← аварийное состояние
│ ├── [L1] Security Center
│ └── [L1] Settings
│ ├── Connect Source
│ ├── Notification Rules
│ ├── Integrations
│ └── Profile & Auth
│
└── Overlays / Modals
├── Thread View ← открывается поверх Inbox
├── Quick Reply
├── Snooze Picker
└── Priority Override

1.2 Навигационная модель

Архитектура: Left Sidebar (desktop) / Bottom Tab Bar (mobile) + контекстная панель справа.

Принципы навигации:

Глубина не более 3 уровней (Inbox → Thread → Reply)
Back всегда доступен, но не разрушает состояние (сохраняется scroll, черновик)
Смена режима (Focus/Incident) — не новый экран, а наложение состояния на оболочку
Settings — вне основного рабочего потока, доступны через аватар/иконку

Навигационные элементы:

ЗонаЭлементДействиеSidebar topЛоготип / DashboardВернуться в InboxSidebar mainInbox, Focus, Incident, SecurityПереключение L1-экрановSidebar bottomNotifications bell, AvatarНастройки, профильInbox toolbarSource filters, Sort, SearchФильтрация в рамках InboxThread panelBack, Actions, ContextНавигация внутри тредаStatus barРежим работы, счётчик непрочитанныхИндикация состояния

1.3 Состояния приложения (App States)

NORMAL ──────→ FOCUS MODE (активирован вручную или по расписанию)
│ │
│ └──→ NORMAL (таймер истёк / отключён вручную)
│
└──→ INCIDENT MODE (P0-алерт / активирован вручную)
│
└──→ NORMAL (инцидент закрыт / dismissed)

2. Пользовательские флоу

2.1 Onboarding

Happy Path

Шаг 1: Welcome Screen
──────────────────────
Триггер: первый запуск после установки / создания аккаунта
Экран: полноэкранный, без chrome (нет sidebar, нет nav)

Контент:
→ Logotype + tagline: "Все входящие. Один приоритет."
→ Иллюстрация: схематичный inbox с цветными источниками
→ CTA: [Начать] (primary) / [Войти] (secondary)

Пользователь нажимает [Начать]
↓

Шаг 2: Account Setup
──────────────────────
Форма: Email / пароль или OAuth (Google, GitHub, Microsoft)
Inline-валидация (не submit-validation)
Checkbox: "Я соглашаюсь с Terms" — обязательно, но не мелким шрифтом

Пользователь заполняет → нажимает [Создать аккаунт]
↓

Шаг 3: "Откуда получаете сообщения?"
────────────────────────────────────
Экран-решётка: карточки источников (Email, Slack, GitHub, Jira, PagerDuty, Telegram…)
Каждая карточка: иконка + название + 1 строка описания
Multi-select (можно выбрать несколько)
Progress indicator: "Шаг 1 из 2" (не говорим "3 из 3", чтобы не пугать)

Минимум: нужно выбрать ≥1
CTA: [Подключить выбранные] / Skip-link: "Настрою позже" (мелкий, под кнопкой)

Пользователь выбирает Gmail + Slack → нажимает [Подключить выбранные]
↓

Шаг 4: Connect Source Flow (подробно в 2.2)
Пользователь последовательно авторизует каждый источник
↓

Шаг 5: Tutorial Overlay (после первой синхронизации)
──────────────────────────────────────────────────────
Не carousel из 7 слайдов — этого никто не читает.
Вместо этого: 3 Coach Mark'а поверх реального интерфейса:

1. Sidebar → "Ваши источники здесь. Нажмите для фильтра."
2. Priority tag на письме → "Мы расставили приоритеты. Вы можете их переопределить."
3. Focus Mode кнопка → "Режим без отвлечений — здесь."

CTA на каждом: [Понятно] / [Пропустить всё]
После третьего или Skip → Tutorial dismissed навсегда

↓
Финал: Unified Inbox, первое письмо открыто для ознакомления

Error Path

Ошибка E1: Email уже существует
→ Inline error под полем: "Этот email уже используется. Войдите или сбросьте пароль."
→ CTA трансформируется: [Войти с этим email] (pre-filled)

Ошибка E2: OAuth провалился (нет сети / провайдер недоступен)
→ Toast (не блокирующий): "Не удалось подключиться к Google. Попробуйте ещё раз или используйте email."
→ Форма остаётся доступной

Ошибка E3: Пользователь прошёл Onboarding, не подключил ни одного источника (нажал Skip)
→ Попадает в Inbox в Empty State #1 (см. раздел 5)
→ Sticky banner вверху: "Добавьте источник, чтобы начать работу" + [Подключить]

Ошибка E4: Сессия истекла во время онбординга
→ При попытке Submit: "Сессия истекла. Данные сохранены — войдите снова."
→ Перенаправление на Login с pre-fill email

2.2 Connect Source

Happy Path

Шаг 1: Источник выбран (из Onboarding или Settings → Connect Source)
──────────────────────────────────────────────────────────────────────
Экран: Modal / Full-panel (зависит от контекста — onboarding vs settings)

Состав:
→ Иконка + название источника (Gmail)
→ Краткое описание: "Мы получим доступ только к чтению входящих"
→ Список разрешений в human-readable формате (не scope-строки OAuth)
→ [Подключить через Google] / [Назад]

Пользователь нажимает [Подключить через Google]
↓

Шаг 2: OAuth Handoff
─────────────────────
→ Открывается OAuth-окно провайдера (системный браузер или webview)
→ В приложении: placeholder "Ожидание авторизации в Google…" + spinner
→ Timeout: 120 сек. После — Error Path E1

Пользователь проходит OAuth в браузере → возвращается в приложение
↓

Шаг 3: Конфигурация источника (необязательный)
──────────────────────────────────────────────
Для сложных источников (Jira, GitHub):
→ Выбор workspace / организации / репозиториев
→ Checkboxes: какие события импортировать (Issues, PRs, CI, Security alerts)
→ Preview: "Примерно X писем за последние 7 дней"

Для простых (Gmail): этот шаг пропускается
↓

Шаг 4: Синхронизация
─────────────────────
→ Progress bar: "Синхронизируем последние 30 дней…"
→ Живой счётчик: "Загружено: 1 247 сообщений"
→ Не блокирует: можно нажать [Продолжить работу] — синхронизация идёт в фоне

↓
Финал: Toast "Gmail подключён" + источник появляется в sidebar-фильтре

Error Path

Ошибка E1: OAuth timeout (пользователь не завершил в браузере)
→ "Авторизация не завершена. Окно браузера всё ещё открыто — или [Начать заново]."
→ Кнопка "Начать заново" сбрасывает flow без потери прогресса других источников

Ошибка E2: Отзыв разрешений / недостаточно прав
→ "Google не предоставил нужные разрешения. Нам нужен доступ к [список] для работы."
→ Ссылка [Показать инструкцию] → открывает Help overlay
→ [Попробовать снова] — перезапускает OAuth с явным указанием требуемых scopes

Ошибка E3: Источник уже подключён с другого аккаунта
→ "Этот Gmail-аккаунт уже используется в другом профиле."
→ Опции: [Использовать здесь] (перенести) / [Подключить другой аккаунт]

Ошибка E4: Синхронизация прервана (сеть пропала)
→ Toast: "Синхронизация прервана. Мы продолжим, когда появится соединение."
→ В sidebar: иконка источника с ⟳ и "Ожидание сети"
→ Автоматическое возобновление без участия пользователя

Ошибка E5: Rate limit от провайдера
→ "Gmail временно ограничил импорт. Мы продолжим через ~15 минут автоматически."
→ Прогресс сохранён, пользователь не блокирован

2.3 Unified Inbox

Happy Path

Шаг 1: Пользователь открывает приложение
─────────────────────────────────────────
→ Sidebar: логотип, навигация, источники с бейджами непрочитанных
→ Основная панель: список сообщений

СТРУКТУРА ЭКРАНА (wireframe-описание):
┌─────────────────────────────────────────────────────────────┐
│ [≡ Logo] Inbox [🔍 Search] [Focus] [⚙ Settings] │
├──────────────┬──────────────────────────────────────────────┤
│ SIDEBAR │ TOOLBAR │
│ │ [All ▼] [Gmail ○] [Slack ○] [Jira ○] [+] │
│ 📥 Inbox 12 │ Sort: Smart ▼ Filter: Unread ▼ │
│ 🎯 Focus ├──────────────────────────────────────────────┤
│ 🚨 Incident │ MESSAGE LIST │
│ 🔒 Security │ │
│ │ ┌─────────────────────────────────────────┐ │
│ ─────────── │ │ 🔴 P0 [PagerDuty] DB replication lag │ │
│ SOURCES │ │ Production · 3 min ago · CRITICAL │ │
│ Gmail · 7 │ └─────────────────────────────────────────┘ │
│ Slack · 3 │ ┌─────────────────────────────────────────┐ │
│ GitHub · 2 │ │ 🟠 P1 [Slack] @you: Deploy blocker #427│ │
│ Jira · 0 │ │ #backend · 8 min ago · Vasyl K. │ │
│ │ └─────────────────────────────────────────┘ │
│ [+ Add src] │ ┌─────────────────────────────────────────┐ │
│ │ │ 🟡 P2 [Gmail] Ревью контракта до пятни │ │
│ ─────────── │ │ hr@company · 2 h ago │ │
│ 👤 Profile │ └─────────────────────────────────────────┘ │
│ 🔔 Alerts 1 │ │
└──────────────┴──────────────────────────────────────────────┘

Шаг 2: Пользователь просматривает список
──────────────────────────────────────────
→ Сортировка по умолчанию: Smart Sort (приоритет × время)
→ Строка сообщения показывает:

- Цветной P-индикатор (P0=красный, P1=оранжевый, P2=жёлтый, P3=серый)
- Иконка источника (брендовая)
- Тема / первая строка превью
- Контекст (канал/папка, время, отправитель)
  → Hover/long-press: Quick Actions (Archive, Snooze, Pin, Mark as done)

Шаг 3: Клик на сообщение → Thread View (2.4)

Error Path

Ошибка E1: Источник потерял авторизацию (токен истёк)
→ В sidebar рядом с источником: ⚠️ иконка
→ Inline banner в списке (не весь экран, не модал):
"Gmail требует переподключения. [Восстановить доступ]"
→ Сообщения из этого источника остаются, помечены "последнее обновление X ч. назад"

Ошибка E2: Нет интернета
→ Offline banner (top strip, желтый): "Нет соединения. Показаны кешированные сообщения."
→ Работает в read-only: чтение, сортировка, теги
→ Действия (Reply, Archive) ставятся в очередь и синхронизируются автоматически

Ошибка E3: Пришло слишком много сообщений (> 500 за сессию)
→ Не показываем 500 строк. Группировка:
"GitHub: 312 новых уведомлений → [Показать все] / [Сводка]"
→ Сводка = AI-дайджест: "3 PR требуют вашего ревью. 1 CI упал в main."

Ошибка E4: Синхронизация зависла (нет обновлений > 30 мин)
→ Статусная строка в sidebar под источником: "Обновлено 34 мин. назад · ⟳"
→ При клике: принудительная синхронизация + диагностика

2.4 Thread View

Happy Path

Шаг 1: Открытие треда
──────────────────────
→ Thread View открывается как правая панель (split view на desktop)
или как full-screen overlay (mobile / узкий viewport)
→ Анимация: slide-in справа, не fade (сохраняет ориентацию)

СТРУКТУРА ЭКРАНА:
┌──────────────────────────────────────────────────────────┐
│ ← Назад [PagerDuty] DB replication lag [⋮ Actions] │
├───────────────────────────────┬──────────────────────────┤
│ THREAD │ CONTEXT PANEL │
│ │ │
│ 🔴 P0 CRITICAL │ Связанные элементы: │
│ 14:23 · PagerDuty │ • Jira: INFRA-2847 │
│ ───────────────────── │ • Slack: #oncall │
│ DB replication lag: │ • GitHub: deploy #934 │
│ 14.5s (threshold: 2s) │ │
│ │ История инцидентов: │
│ Assigned: @you │ Последний: 12 дней назад │
│ Region: eu-west-1 │ │
│ [Acknowledge] [Escalate] │ Runbook: [Открыть →] │
│ │ │
│ 14:25 · Vasyl K. (Slack) │ Команда: │
│ "Вижу проблему, смотрю логи" │ • @vasyl — online │
│ │ • @olena — offline │
│ [Ответить в Slack] [Gmail] │ │
├───────────────────────────────┴──────────────────────────┤
│ REPLY COMPOSER │
│ Ответить в: [PagerDuty ▼] [Slack #oncall ▼] │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Написать ответ… │ │
│ └────────────────────────────────────────────────────┘ │
│ [AI Draft] [Attach] [Schedule ▼] [Отправить] │
└──────────────────────────────────────────────────────────┘

Шаг 2: Взаимодействие
──────────────────────
→ Inline actions на каждом сообщении: Reply, React, Copy link, Forward
→ Cross-source reply: выбор куда отвечать (в тот же канал или в другой)
→ Context Panel разворачивается/сворачивается (по умолчанию развёрнута для P0/P1)
→ AI Draft: предлагает черновик ответа в 1 клик — пользователь редактирует, не принимает вслепую

Шаг 3: Закрытие треда
──────────────────────
→ Действия: [Mark as Done] / [Archive] / [Snooze] / [Escalate to Incident]
→ После Done: плавно исчезает из списка, фокус переходит на следующий элемент
→ Undo доступен 5 секунд через snackbar: "Отмечено выполненным · Отменить"

Error Path

Ошибка E1: Сообщение удалено на стороне источника
→ "Это сообщение было удалено в Slack. Показана кешированная версия."
→ Действия-мутации (Reply, Forward) заблокированы с объяснением
→ Read-only badge: "Только просмотр"

Ошибка E2: Ошибка отправки ответа
→ Composer: сообщение помечается 🔴 "Не доставлено"
→ Inline: [Повторить] / [Сохранить черновик]
→ Черновик автосохраняется каждые 10 сек (не нужно просить)

Ошибка E3: Тред содержит 1000+ сообщений
→ Показываем первые 5 + последние 15
→ "Пропущено 980 сообщений · [Загрузить всё] / [Найти в треде]"
→ Поиск внутри треда работает без полной загрузки

Ошибка E4: Контекстная панель не загружается (Jira недоступна)
→ В Context Panel: placeholder с иконкой ⚠️ + "Jira временно недоступна"
→ Thread-view продолжает работать нормально — контекст некритичен

2.5 Focus Mode

СУТЬ: временный режим — пользователь видит только критичное (P0+P1),
все остальные уведомления приглушены, интерфейс упрощён.

АКТИВАЦИЯ:
→ Sidebar: кнопка [🎯 Focus Mode]
→ Keyboard shortcut: Cmd/Ctrl + Shift + F
→ Автоматически: расписание в Settings (напр., 09:00–11:00 каждый день)

WIREFRAME:
┌──────────────────────────────────────────────────────────┐
│ 🎯 FOCUS MODE ● Ещё 47 мин. [Выйти] │
├──────────────────────────────────────────────────────────┤
│ │
│ Сейчас важно: │
│ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🔴 DB replication lag · PagerDuty · 3 мин. назад │ │
│ │ Требует действия [Открыть] │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🟠 Deploy blocker #427 · Slack · 8 мин. назад │ │
│ │ Ждут вашего ответа [Открыть] │ │
│ └─────────────────────────────────────────────────────┘ │
│ │
│ Остальное: 34 новых · будут ждать до конца сессии │
│ │
│ ──────────────────────────────────────────────────── │
│ 📊 Статистика сессии: │
│ Обработано: 5 Среднее время ответа: 4.2 мин. │
└──────────────────────────────────────────────────────────┘

ФЛОУ:
Шаг 1: Активация → режим включается мгновенно (не нужно confirm)
Шаг 2: Пользователь видит только P0/P1, всё остальное скрыто
Шаг 3: Входящий P0 во время Focus → всё равно показывается (не блокируется)
Шаг 4: Входящий P2 во время Focus → попадает в очередь, не уведомляет
Шаг 5: Сессия завершается (таймер / вручную) → Brief сводка + возврат в Inbox

ВЫХОД ИЗ FOCUS:
→ [Выйти] в любой момент → мгновенный возврат
→ По таймеру → мягкое уведомление "Фокус-сессия завершена, 34 сообщения ждут"
→ При входящем P0 — система НЕ прерывает Focus, но добавляет в список выше
→ ИСКЛЮЧЕНИЕ: Incident Mode всегда перекрывает Focus (см. 2.6)

2.6 Incident Mode

СУТЬ: аварийный режим — полный экран, только инцидент, все инструменты
для тушения пожара в одном месте. Аналог war room в одном экране.

АКТИВАЦИЯ:
→ Автоматически: входящий алерт P0 с тегом "incident" / настроенные правила
→ Вручную: [Объявить инцидент] в любом экране
→ Из Thread View: кнопка [Escalate to Incident]

WIREFRAME:
┌──────────────────────────────────────────────────────────┐
│ 🚨 INCIDENT MODE [Закрыть инцидент] [Pause] │
│ DB Replication Crisis · eu-west-1 · P0 · 14:23 UTC │
├───────────────────────────────┬──────────────────────────┤
│ TIMELINE │ ACTIONS │
│ │ │
│ 14:23 🔴 Алерт: lag 14.5s │ [Acknowledge] │
│ 14:25 💬 Vasyl: "смотрю логи" │ [Page On-call] │
│ 14:27 📋 Jira INFRA-2847 open │ [Post Status Update] │
│ 14:29 ⚡ Deploy #934 rolled │ [Escalate to P0 Team] │
│ back automatically │ [Open Runbook] │
│ 14:31 ✅ You: "ack'd" │ [Create War Room] │
│ │ │
│ [Добавить заметку…] │ ───────────────────── │
│ │ AFFECTED: │
├───────────────────────────────┤ 3 services │
│ QUICK STATS │ eu-west-1 region │
│ Длительность: 00:08:32 │ ~1200 users │
│ SLA риск: 🟠 Medium │ │
│ MTTR цель: < 30 мин. │ RESPONDERS: │
│ │ • @vasyl 🟢 active │
│ [PagerDuty ↗] [Grafana ↗] │ • @olena 🔴 paged │
└───────────────────────────────┴──────────────────────────┘

ФЛОУ:
Шаг 1: Триггер → Incident Mode активируется с аудио-сигналом (если не muted)
→ Все другие режимы (включая Focus) прерываются
Шаг 2: Экран захватывает полное пространство — никаких других уведомлений
Шаг 3: Timeline формируется автоматически из всех источников по инциденту
Шаг 4: Пользователь работает с Actions — каждое действие логируется в Timeline
Шаг 5: [Закрыть инцидент] → Post-mortem шаблон заполняется автоматически
Шаг 6: Возврат в Inbox — инцидент архивируется с полным логом

ЗАЩИТА:
→ Закрытие инцидента требует подтверждения: "Инцидент устранён? [Да, закрыть] / [Нет]"
→ Случайный Close (без confirm) невозможен — нет крестика в углу

2.7 Security Center

СУТЬ: мониторинг аномалий, управление доступом, аудит действий.
Не навязчивый, не кричащий — но информативный и actionable.

АКТИВАЦИЯ: Sidebar → [🔒 Security] / автоматически при Security Alert P0

WIREFRAME:
┌──────────────────────────────────────────────────────────┐
│ 🔒 Security Center Последнее сканирование: 2ч. │
├──────────────────────────────────────────────────────────┤
│ СТАТУС: ● 2 предупреждения требуют внимания │
├──────────────────────────────┬───────────────────────────┤
│ АНОМАЛИИ (2) │ ДЕТАЛИ СОБЫТИЯ │
│ │ │
│ ⚠️ Новое устройство │ ⚠️ Новое устройство │
│ Вход с Kyiv · 10:14 │ │
│ Chrome / Windows │ IP: 194.xxx.xxx.xxx │
│ [Это я] [Заблокировать] │ Kyiv, UA │
│ │ Chrome 124 / Windows 11 │
│ ⚠️ Необычное время │ Время: 10:14 UTC │
│ Gmail доступ в 03:22 │ │
│ [Просмотреть] [Dismiss] │ Первый вход с этого IP │
│ │ │
├──────────────────────────────┤ [✅ Это я] │
│ ИНТЕГРАЦИИ (3 активных) │ [🚫 Заблокировать] │
│ │ [📋 Подробный лог] │
│ ● Gmail — читать письма │ │
│ ● Slack — читать каналы │ │
│ ● GitHub — repos + CI │ │
│ │ │
│ [Управление доступом] │ │
├──────────────────────────────┴───────────────────────────┤
│ АУДИТ-ЛОГ (последние 7 дней) [Экспорт CSV] │
│ 10:14 · Новый вход · Kyiv · Chrome │
│ 09:43 · Reply отправлен через Gmail · вы │
│ 09:12 · Синхронизация Slack · автоматически │
└──────────────────────────────────────────────────────────┘

ФЛОУ:
Шаг 1: Пользователь заходит → видит Security Score + список аномалий
Шаг 2: Нажимает на аномалию → правая панель заполняется деталями
Шаг 3: Принимает решение: [Это я] (dismiss) или [Заблокировать]
Шаг 4: При блокировке → сессия завершается удалённо + уведомление на email
Шаг 5: История хранится 90 дней, экспортируется в CSV/JSON

АЛЕРТЫ:
→ P0 Security: вход с неизвестного IP + незнакомое устройство + ночное время
→ Немедленный push + email + модал в приложении (не dismissable без действия)
→ P1 Security: только один из факторов
→ Badge в sidebar, не прерывает работу

3. Правила приоритизации уведомлений

3.1 Уровни приоритета

УровеньЦветНазваниеОписаниеПоведениеP0🔴 КрасныйCriticalТребует немедленного действияPush + звук + прерывает FocusP1🟠 ОранжевыйUrgentТребует ответа сегодняPush тихий, не прерываетP2🟡 ЖёлтыйImportantТребует внимания на этой неделеBadge толькоP3⚪ СерыйNormalРабочий потокТолько в спискеP4—LowИнформационное / FYIСкрыто по умолчанию

3.2 Алгоритм скоринга

ПРИОРИТЕТ = f(Source Weight, Sender Rank, Content Signals, Time Decay, User Behavior)

──────────────────────────────────────────────────────
A. SOURCE WEIGHT (вес источника)
──────────────────────────────────────────────────────
PagerDuty / OpsGenie / VictorOps → +60 (incidents)
Security alerts (любой источник) → +60 (auth, anomaly)
GitHub CI: failed / blocked → +40
Slack DM (прямое упоминание @you) → +35
Jira: assigned to you → +30
GitHub PR: review requested → +25
Gmail: direct email → +20
Slack: channel mention → +15
GitHub: star / watch → +5
Newsletter / Digest → -20

──────────────────────────────────────────────────────
B. SENDER RANK (кто прислал)
──────────────────────────────────────────────────────
Определяется поведением пользователя, не должностью:
Часто читает + отвечает быстро → High (+20)
Читает, но отвечает медленно → Medium (+10)
Редко открывает → Low (+0)
Никогда не отвечал → Noise (-10)

Переопределяется вручную: "Всегда P1 от boss@company.ua"

──────────────────────────────────────────────────────
C. CONTENT SIGNALS (сигналы из контента)
──────────────────────────────────────────────────────
Ключевые слова в теме/теле:
CRITICAL / OUTAGE / DOWN / URGENT / ASAP → +30
action required / needs your review → +20
FYI / newsletter / unsubscribe → -15
[SPAM] / no-reply → -30

Структура:
Упомянут напрямую (@username) → +25
CC (не TO) → -10
BCC → -15

──────────────────────────────────────────────────────
D. TIME DECAY
──────────────────────────────────────────────────────
Сообщение < 30 мин. → ×1.0 (без штрафа)
Сообщение < 4 ч. → ×0.9
Сообщение < 24 ч. → ×0.7
Сообщение > 24 ч. → ×0.5
Старше 3 дней → ×0.3

Исключение: P0-алерты не деградируют по времени

──────────────────────────────────────────────────────
E. USER BEHAVIOR (адаптивное обучение)
──────────────────────────────────────────────────────
Пользователь игнорирует Slack из канала #random → канал понижается
Пользователь всегда отвечает на письма от hr@ → hr@ повышается
Пользователь вручную переопределяет приоритет → правило запоминается

Обучение: после 5 однотипных действий — правило предлагается явно:
"Вы 5 раз архивировали GitHub Watch без прочтения.
Перевести в P4 автоматически? [Да] / [Нет, спросить позже]"

──────────────────────────────────────────────────────
ИТОГОВЫЙ РАСЧЁТ:
──────────────────────────────────────────────────────
Score = (A + B + C) × D + E-adjustment

Score ≥ 80 → P0
Score 50–79 → P1
Score 30–49 → P2
Score 10–29 → P3
Score < 10 → P4

3.3 Ручной override

На любом сообщении пользователь может:
→ Нажать на P-бейдж → Popover с уровнями P0–P4
→ Выбрать другой уровень → применяется немедленно
→ Опционально: "Запомнить правило для этого источника/отправителя"

Override всегда показывает причину текущего приоритета:
"P1 потому что: упомянут напрямую (+25) + Jira assigned (+30) + Andrey H. (High sender +20)"

Прозрачность = доверие.

3.4 Защита от Priority Inflation

Проблема: если всё P0 — ничто не P0.

Правила:
→ Максимум 3 P0 одновременно (4-й входящий P0 → автоматически предлагается объединить)
→ P0 без действия > 30 мин → мягкий запрос: "Этот алерт всё ещё актуален?"
→ Weekly summary: "На прошлой неделе было 47 P0. Слишком много? [Настроить правила]"

4. Empty States & Error States

4.1 Empty States

EMPTY STATE #1: Нет подключённых источников (новый пользователь)
────────────────────────────────────────────────────────────────
Иллюстрация: пустой inbox с пунктирными контурами (намёк на то, что будет)
Заголовок: "Здесь будут ваши сообщения"
Описание: "Подключите Gmail, Slack или любой другой источник — и все входящие окажутся в одном месте."
CTA: [Подключить первый источник] (primary, крупный)

НЕ ДЕЛАЕМ: "Нет данных", "Nothing here yet" — это пустые слова.
ДЕЛАЕМ: Явное приглашение к действию с понятным результатом.

──────────────────────────────────────────────────────────────
EMPTY STATE #2: Всё прочитано / обработано (inbox zero)
────────────────────────────────────────────────────────────────
Иллюстрация: минималистичная, лёгкая (не достижение, не фанфары — продуктивное спокойствие)
Заголовок: "Всё обработано"
Описание: "Следующие сообщения появятся здесь."
Дополнительно: "Следующая синхронизация: через 2 мин." (технический контекст)
НЕТ CTA (не нужно навязывать действие)

──────────────────────────────────────────────────────────────
EMPTY STATE #3: Фильтр не даёт результатов
────────────────────────────────────────────────────────────────
Иллюстрация: лупа с пустым экраном
Заголовок: "Ничего не найдено"
Описание: "В Slack за последние 7 дней нет непрочитанных сообщений с высоким приоритетом."
CTA: [Сбросить фильтры] + ссылка "Изменить временной диапазон"

──────────────────────────────────────────────────────────────
EMPTY STATE #4: Focus Mode — нет критических сообщений
────────────────────────────────────────────────────────────────
Заголовок: "Ничего срочного"
Описание: "34 сообщения ждут конца сессии. Сфокусируйтесь."
НЕ ПОКАЗЫВАЕМ эти 34 — это нарушило бы смысл Focus.

──────────────────────────────────────────────────────────────
EMPTY STATE #5: Security Center — нет аномалий
────────────────────────────────────────────────────────────────
Иконка: зелёный щит
Заголовок: "Всё в порядке"
Описание: "Аномалий не обнаружено. Последнее сканирование: 2 часа назад."
Ссылка: "Просмотреть аудит-лог" (для тех, кто хочет убедиться)

4.2 Error States

ERROR STATE #1: Полная потеря соединения
─────────────────────────────────────────
Тип: Non-blocking top banner (не full-screen)
Содержание: "⚠️ Нет соединения · Показаны данные на 14:23 · Восстановление…"
Поведение: Исчезает автоматически при восстановлении
НЕ ДЕЛАЕМ: Блокирующий модал — пользователь теряет контекст

──────────────────────────────────────────────────────────────
ERROR STATE #2: Источник недоступен
────────────────────────────────────────────────────────────────
Тип: Inline в sidebar (иконка ⚠️ рядом с источником)
При hover/tap: тултип "Gmail недоступен с 14:05. Последние данные актуальны."
В списке: сообщения из этого источника отмечены "не обновлялось X мин."
Глобальный экран не занимаем — один источник не должен блокировать работу.

──────────────────────────────────────────────────────────────
ERROR STATE #3: Ошибка отправки ответа
────────────────────────────────────────────────────────────────
Тип: Inline в composer
Иконка 🔴 + текст "Не доставлено · Slack вернул ошибку"
Actions: [Повторить] / [Скопировать текст] / [Открыть в Slack]
НЕ ТЕРЯЕМ текст — черновик всегда в очереди

──────────────────────────────────────────────────────────────
ERROR STATE #4: Ошибка загрузки треда
────────────────────────────────────────────────────────────────
Тип: В Thread View вместо контента
Скелетон 1 сек → если не загрузился: иконка + "Не удалось загрузить"
Actions: [Повторить] / [Открыть в Gmail]
Сохраняем превью из списка — пользователь видел его там

──────────────────────────────────────────────────────────────
ERROR STATE #5: Критическая ошибка приложения (crash)
────────────────────────────────────────────────────────────────
Full-screen (единственный случай полного перехвата)
Содержание: "Что-то пошло не так. Ваши данные сохранены."
Actions: [Перезапустить] / [Сообщить об ошибке]
Под капотом: автоматически отправляем crash report

5. UX-принципы против перегрузки пользователя

Принцип 1: Inbox как инструмент, не задача

Антипаттерн: Показывать все 847 сообщений сразу.
Правило: Показываем релевантные сейчас. Остальное — по запросу.

Реализация:
→ По умолчанию: Smart Sort (приоритет × время), не хронология
→ Максимум 50 элементов без скролла — остальные загружаются по требованию
→ Группировка burst-уведомлений: "GitHub: 47 новых → [Сводка]"
→ Digest для P3/P4: не каждое уведомление отдельно, а ежечасный блок

Принцип 2: Одно действие — одно намерение

Антипаттерн: Quick Actions на hover с 8 кнопками.
Правило: 3 действия максимум на первичном уровне. Остальное — в меню [⋮].

Иерархия действий:
Primary (видно всегда): Done / Reply  
 Secondary (hover): Snooze / Archive  
 Tertiary (меню): Forward / Pin / Priority Override / Copy link

Принцип 3: Не прерывать без причины

Правило прерывания:
P0 Security + P0 Incident → ВСЕГДА прерывает, любой режим
P0 обычный → Push + звук, не прерывает Focus
P1 → Тихий push, только badge в Focus
P2 и ниже → Только badge, никогда push

Do Not Disturb:
→ Расписание DnD в Settings: "Не беспокоить с 22:00 до 09:00"
→ Исключение из DnD: только P0 Security / Incident
→ Без исключений: пользователь сам добавляет через Settings

Принцип 4: Прозрачность алгоритма

Антипаттерн: "Умная сортировка" без объяснений — пользователь не доверяет.
Правило: Всегда объяснять, почему P0/P1. Всегда давать override.

Реализация:
→ P-бейдж кликабелен → Popover с объяснением: "P1 потому что: @mention (+25) + Jira assigned (+30)"
→ Правила приоритизации видны в Settings → Notification Rules
→ Обратная связь: [Это неверный приоритет] → улучшает модель

Принцип 5: Восстановление без потерь

Правило: Любое деструктивное действие обратимо 30 секунд.
Потеря данных (текст ответа, статус) — никогда.

Реализация:
→ Archive / Done / Delete → Undo snackbar, 30 сек.
→ Reply composer → автосохранение каждые 10 сек, черновики сохраняются при закрытии
→ Офлайн-действия → очередь, синхронизируются при подключении
→ "Случайное" закрытие треда → состояние восстанавливается при возврате

Принцип 6: Прогрессивное раскрытие

Правило: Показывать минимум, необходимый для принятия решения.
Детали — по запросу.

Inbox: Иконка + Тема + Превью 1 строка + Время + P-индикатор
Thread Preview: Первые 3 сообщения + [Загрузить всё]
Context Panel: Свёрнута по умолчанию для P2 и ниже, развёрнута для P0/P1
Security: Score + топ-2 аномалии → полный список по клику

Принцип 7: Уважение к вниманию

Антипаттерн: Геймификация inbox ("Вы обработали 100 сообщений! 🎉")
Anxiety-driven design (красные бейджи везде)
Push-уведомления для маркетинга

Правило:
→ Никаких gamification элементов в core flow
→ Бейджи — только для реально непрочитанного, без накопления "фантомных" счётчиков
→ Push только для сообщений, требующих действия (P0/P1)
→ Focus Mode не показывает "сколько накопилось" — это намеренно
→ Статистика — в отдельном разделе, не в основном потоке

Принцип 8: Контекст не теряется при переключении

Правило: Переключение между режимами/экранами — не разрушает состояние.

Реализация:
→ Ушёл в Security Center → вернулся в Inbox → та же позиция скролла
→ Открыл Thread → переключился на другой → оба сохранены (tab-like behaviour)
→ Activating Focus Mode → не закрывает открытый тред, помещает его сверху списка
→ Incident Mode → при закрытии возвращает в тот экран, с которого ушёл

6. Ключевые решения и обоснование

РешениеОбоснованиеSplit-view вместо full-screen ThreadНе теряем контекст списка; можно работать с тредом и одновременно видеть следующийContext Panel по умолчанию открыта для P0/P1High-priority items требуют максимум контекста; остальным он мешаетIncident Mode перекрывает FocusSafety over productivity — нельзя пропустить аварию из-за режима фокусаDigest для низкоприоритетныхGitHub-звёздочки не должны конкурировать с outage-алертамиUndo вместо Confirm для Archive/DoneConfirm interrupts flow; Undo позволяет действовать быстро с возможностью коррекцииОбъяснение приоритета в UIЧёрный ящик → недоверие; прозрачность → доверие → меньше ручных overrideМаксимум 3 P0 одновременноЕсли всё критично — ничто не критично; приоритет должен быть редкимOffline-first с очередью действийМобильные пользователи в метро не должны терять работу из-за сети

UX Document v1.0 · Unified Inbox · Last updated: 2026

### Шаг 5: Technical Architect

Промпт:

Ты staff engineer. Подготовь техническую архитектуру unified inbox (без кода).

Условия:

- Адаптерная модель коннекторов.
- Unified event schema.
- Очередь событий/event bus.
- Шифрование и управление ключами.
- Offline cache и sync strategy.
- Plugin SDK для новых источников.

Сделай:

1. Высокоуровневая архитектура (модули и связи).
2. Набор ADR (решение, альтернативы, trade-offs).
3. Структура БД (многопользовательская модель и изоляция).
4. План реализации на 6 недель (по спринтам).
5. Технические риски и mitigation.

Формат:

- Архитектурные блоки + таблица ADR.

#### Ответ агента (вставь сюда)

Unified Inbox — Техническая Архитектура

Статус: RFC Draft v1.0 · Дата: 2026-06-25 · Роль: Staff Engineer

Содержание

Высокоуровневая архитектура
Unified Event Schema
ADR — Architecture Decision Records
Структура БД
6-недельный план реализации
Технические риски и Mitigation
Приложения

1. Высокоуровневая архитектура

1.1 Диаграмма модулей

┌────────────────────────────────────────────────────────────────────────────┐
│ CLIENT LAYER │
│ Web SPA │ Mobile App │ REST / gRPC │
└────────────────────────────────────────────────────────────────────────────┘
│ HTTPS / WebSocket
┌────────────────────────────────────────────────────────────────────────────┐
│ API GATEWAY │
│ JWT / OAuth2 Auth · Rate Limiting · Request Routing · TLS Term. │
└────────────────────────────────────────────────────────────────────────────┘
│ │ │
┌─────────┴────────┐ ┌────────────┴─────────┐ ┌──────────┴──────────┐
│ INBOX SERVICE │ │ SYNC SERVICE │ │ PLUGIN REGISTRY │
│ Thread mgmt │ │ Offline cache mgmt │ │ Plugin loader │
│ Labels / Tags │ │ Conflict resolution │ │ WASM sandbox │
│ Full-text search│ │ Delta sync cursors │ │ SDK versioning │
└──────────────────┘ └──────────────────────┘ └─────────────────────┘
│ │ │
┌────────────────────────────────────────────────────────────────────────────┐
│ EVENT BUS │
│ topic: raw.events · topic: normalized.events · topic: dlq · topic: audit │
│ Redis Streams (primary) / Kafka (scale-out) │
└────────────────────────────────────────────────────────────────────────────┘
│ │ │ │
┌────┴──────┐ ┌──────┴─────────┐ ┌──────┴─────────┐ ┌──────┴──────────┐
│ CONNECTOR │ │ NORMALIZATION │ │ ENCRYPTION │ │ AUDIT LOG │
│ LAYER │ │ ENGINE │ │ SERVICE │ │ SERVICE │
│ │ │ │ │ │ │ │
│ Adapter │ │ Schema valid. │ │ KMS (envelope) │ │ Immutable │
│ Registry │ │ Field mapper │ │ Key rotation │ │ append-only │
│ │ │ Dedup (hash) │ │ Field-level │ │ WORM storage │
│ ──────── │ │ │ │ enc / dec │ │ │
│ Email │ └────────────────┘ └────────────────┘ └─────────────────┘
│ Slack │
│ Teams │
│ SMS / WA │
│ [Plugin] │
└───────────┘
│
┌────────────────────────────────────────────────────────────────────────────┐
│ STORAGE LAYER │
│ PostgreSQL (RLS) │ Redis Cluster (cache) │ S3-compatible (attachments)│
│ Tenant isolation │ Sync cursors · TTL │ CDN + signed URLs │
└────────────────────────────────────────────────────────────────────────────┘

1.2 Описание модулей

МодульЗона ответственностиКоммуникацияAPI GatewayAuthN/AuthZ, rate limiting, маршрутизация, TLS terminationВходящий трафик → микросервисыInbox ServiceУправление тредами, лейблами, поиском, пагинациейREST/gRPC; читает из PostgreSQLSync ServiceOffline cache, разрешение конфликтов, delta syncWebSocket push; Redis cursorsPlugin RegistryЗагрузка, версионирование, изоляция WASM-плагиновPlugin SDK API; event bus subscriptionEvent BusБуферизация событий, гарантия доставки, топик-роутингKafka / Redis StreamsConnector LayerАдаптеры под каждый источник, polling/webhookПубликует в raw.eventsNormalization EngineВалидация, маппинг, дедупликация, обогащениеЧитает raw.events → пишет normalized.eventsEncryption ServiceEnvelope encryption, key rotation, field-level dec/encСинхронный gRPC (low-latency)Audit Log ServiceImmutable append-only лог всех действийЧитает topic: auditStorage LayerPostgreSQL (RLS), Redis, S3Используется всеми сервисами

2. Unified Event Schema

Все источники сериализуют события в единую обёртку. Схема версионирована.

json{
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
"to": [ { "name": "string", "address": "string" } ],
"cc": [],
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

Ключевые принципы схемы:

UUID v7 как eventId — хронологически сортируемые, k-sortable для B-Tree индексации.
Encrypted fields — body и storageRef шифруются до записи в bus и БД.
Checksum — целостность проверяется на входе Normalization Engine.
Schema versioning — мажорная версия в namespace (/v1, /v2). Backward-compatible эволюция через additive changes.
metadata — свободный словарь для source-специфичных атрибутов без загрязнения core schema.

3. ADR — Architecture Decision Records

IDКонтекст / ВопросПринятое решениеРассмотренные альтернативыTrade-offs и обоснованиеADR-001Выбор технологии Event BusRedis Streams (старт); Kafka (scale-out path)RabbitMQ, NATS JetStream, AWS SQSRedis Streams: zero new infra, at-least-once delivery, consumer groups. Kafka: лучший throughput при >10 K msg/s, но требует KRaft overhead. Переход прозрачен через abstraction layer. RabbitMQ — сложнее replay. SQS — vendor lock-in.ADR-002Формат Unified Event SchemaJSON Schema v7 + ajv validationProtobuf, Apache Avro, MessagePackJSON: человекочитаем, прост для плагинов и SDK. Protobuf — быстрее на больших объёмах, но усложняет Plugin SDK (кодогенерация). Avro — schema registry overhead. На старте JSON достаточен; при >50 K msg/s — dual-write migration на Protobuf.ADR-003Модель изоляции тенантовRow-Level Security (RLS) + tenant_id columnSchema-per-tenant, DB-per-tenantRLS: один connection pool, простые миграции, линейно масштабируется до ~1 000 тенантов. Schema-per-tenant: изолированнее, но pg_connection overhead. DB-per-tenant: максимальная изоляция, но расточительно при SaaS с мелкими тенантами. RLS достаточно при аудите SQL-запросов.ADR-004Стратегия Offline Cache и SyncEvent Sourcing + Delta Sync с cursor-based paginationCRDTs, Last-Write-Wins, OTEvent sourcing: точный replay, конфликты разрешаются детерминированно по timestamp + vector clock. LWW — прост, но теряет данные при конкурентных изменениях. CRDTs — избыточны для inbox (нет collaborative editing). OT — complexity overkill. Cursor хранится в Redis; offline state — в IndexedDB/SQLite на клиенте.ADR-005Стратегия шифрованияEnvelope Encryption (KMS) + Field-Level EncryptionE2E шифрование, Full-disk шифрованиеEnvelope: Data Encryption Key (DEK) шифруется Key Encryption Key (KEK) в KMS. Ротация ключей без перешифровки данных. E2E — сервер не может делать поиск/индексирование. Full-disk — не защищает от утечек через приложение. Field-level для body, address, storageRef.ADR-006Изоляция Plugin SDKWebAssembly (WASM) sandboxSubprocess isolation, Native modules, V8 IsolatesWASM: детерминированное исполнение, memory-safe, capability-based (явные импорты). Subprocess — IPC overhead, OS-process leak риск. Native модули — критический риск: один баг роняет весь процесс. V8 Isolates — только JS/TS плагины. WASM позволяет Rust/C/Go/AssemblyScript SDK.ADR-007Дедупликация событийContent-addressable hash SHA-256 canonical payloadeventId idempotency key, DB unique constraint onlyКоннектор вычисляет externalId + sourceType + timestamp → SHA-256. Normalization Engine проверяет bloom filter (Redis) перед вставкой. DB unique constraint — вторая линия защиты. Только DB constraint недостаточно при высоком throughput (lock contention).

4. Структура БД

4.1 Принципы многопользовательской модели

Каждая таблица содержит tenant_id UUID NOT NULL.
При открытии сессии устанавливается SET LOCAL app.current_tenant_id = '...'.
RLS policy на каждой таблице: USING (tenant_id = current_setting('app.current_tenant_id')::uuid).
Superuser bypass (BYPASSRLS) — только для migration runner service account.

4.2 Схема таблиц

sql-- ─────────────────────────────────────────────────────
-- Тенанты (без RLS — системная таблица)
-- ─────────────────────────────────────────────────────
tenants
id UUID PRIMARY KEY
slug TEXT UNIQUE NOT NULL
display_name TEXT NOT NULL
plan TEXT -- 'free' | 'pro' | 'enterprise'
settings JSONB
created_at TIMESTAMPTZ NOT NULL DEFAULT now()

-- ─────────────────────────────────────────────────────
-- Пользователи
-- ─────────────────────────────────────────────────────
users
id UUID PRIMARY KEY
tenant_id UUID NOT NULL REFERENCES tenants(id)
email BYTEA NOT NULL -- field-encrypted
display_name TEXT
role TEXT NOT NULL -- 'owner' | 'admin' | 'member'
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
[RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Коннекторы (источники)
-- ─────────────────────────────────────────────────────
connectors
id UUID PRIMARY KEY
tenant_id UUID NOT NULL
user_id UUID REFERENCES users(id)
source_type TEXT NOT NULL -- 'email' | 'slack' | 'plugin:<name>'
display_name TEXT
status TEXT NOT NULL -- 'active' | 'paused' | 'error'
config JSONB -- non-sensitive config
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
[RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Учётные данные коннекторов (зашифрованы envelope)
-- ─────────────────────────────────────────────────────
connector_credentials
id UUID PRIMARY KEY
connector_id UUID NOT NULL REFERENCES connectors(id) ON DELETE CASCADE
tenant_id UUID NOT NULL
encrypted_payload BYTEA NOT NULL -- AES-256-GCM, зашифровано DEK
dek_ref TEXT NOT NULL -- ссылка на DEK в encryption_keys
rotated_at TIMESTAMPTZ
[RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Треды (группировка сообщений)
-- ─────────────────────────────────────────────────────
threads
id UUID PRIMARY KEY
tenant_id UUID NOT NULL
user_id UUID NOT NULL REFERENCES users(id)
connector_id UUID NOT NULL REFERENCES connectors(id)
external_thread_id TEXT -- ID треда в источнике
subject TEXT
participant_addresses BYTEA -- field-encrypted JSONB array
first_message_at TIMESTAMPTZ
last_message_at TIMESTAMPTZ
message_count INTEGER NOT NULL DEFAULT 0
labels UUID[]
is_archived BOOL NOT NULL DEFAULT false
is_starred BOOL NOT NULL DEFAULT false
[RLS ENABLED]
INDEX (tenant_id, user_id, last_message_at DESC)
INDEX (tenant_id, connector_id)

-- ─────────────────────────────────────────────────────
-- Сообщения (ядро Unified Inbox)
-- ─────────────────────────────────────────────────────
messages
id UUID PRIMARY KEY -- UUID v7 (хронологически сортируемый)
tenant_id UUID NOT NULL
thread_id UUID NOT NULL REFERENCES threads(id)
connector_id UUID NOT NULL REFERENCES connectors(id)
external_id TEXT NOT NULL -- ID в источнике
dedup_hash TEXT NOT NULL -- SHA-256 canonical hash
source_type TEXT NOT NULL
from_address BYTEA NOT NULL -- field-encrypted
to_addresses BYTEA NOT NULL -- field-encrypted
subject TEXT
body_ref BYTEA -- зашифрованный S3 key
body_preview BYTEA -- первые 200 символов, encrypted
schema_version TEXT NOT NULL DEFAULT '1.0.0'
flags JSONB NOT NULL DEFAULT '{}'
received_at TIMESTAMPTZ NOT NULL
indexed_at TIMESTAMPTZ
[RLS ENABLED]
UNIQUE (tenant_id, dedup_hash)
INDEX (tenant_id, thread_id, received_at DESC)
INDEX (tenant_id, connector_id, received_at DESC)

-- ─────────────────────────────────────────────────────
-- Вложения
-- ─────────────────────────────────────────────────────
attachments
id UUID PRIMARY KEY
tenant_id UUID NOT NULL
message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE
filename TEXT NOT NULL
mime_type TEXT NOT NULL
size_bytes BIGINT NOT NULL
storage_ref BYTEA NOT NULL -- зашифрованный S3 path
checksum TEXT NOT NULL -- SHA-256 plaintext
[RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Метки / Теги
-- ─────────────────────────────────────────────────────
labels
id UUID PRIMARY KEY
tenant_id UUID NOT NULL
user_id UUID REFERENCES users(id)
name TEXT NOT NULL
color TEXT
is_system BOOL NOT NULL DEFAULT false -- Inbox, Sent, Spam, Trash
[RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Курсоры синхронизации (offline sync state)
-- ─────────────────────────────────────────────────────
sync_cursors
id UUID PRIMARY KEY
tenant_id UUID NOT NULL
user_id UUID NOT NULL REFERENCES users(id)
connector_id UUID NOT NULL REFERENCES connectors(id)
cursor_value TEXT NOT NULL -- source-specific (page token, timestamp, etc.)
vector_clock JSONB NOT NULL -- {deviceId: seq} для conflict resolution
synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
[RLS ENABLED]
UNIQUE (tenant_id, user_id, connector_id)

-- ─────────────────────────────────────────────────────
-- Ключи шифрования (Data Encryption Keys)
-- ─────────────────────────────────────────────────────
encryption_keys
id UUID PRIMARY KEY
tenant_id UUID NOT NULL
key_purpose TEXT NOT NULL -- 'messages' | 'credentials' | 'attachments'
dek_ciphertext BYTEA NOT NULL -- DEK, зашифрованный KEK из KMS
kek_ref TEXT NOT NULL -- ссылка на KEK в KMS
algorithm TEXT NOT NULL -- 'AES-256-GCM'
status TEXT NOT NULL -- 'active' | 'rotating' | 'retired'
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
retired_at TIMESTAMPTZ
[RLS ENABLED]

-- ─────────────────────────────────────────────────────
-- Аудит лог (append-only, INSERT-only RLS policy)
-- ─────────────────────────────────────────────────────
audit_log
id UUID PRIMARY KEY
tenant_id UUID NOT NULL
actor_user_id UUID
action TEXT NOT NULL -- 'message.read' | 'connector.created' | ...
resource_type TEXT NOT NULL
resource_id UUID
context JSONB -- IP, user-agent, session_id
occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
[RLS ENABLED; INSERT-ONLY POLICY]

4.3 RLS Policy (пример)

sql-- Установка контекста тенанта при открытии сессии
SET LOCAL app.current_tenant_id = :tenant_id;

-- Политика изоляции на таблице messages
CREATE POLICY tenant_isolation ON messages
USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Audit log: только запись, без чтения через приложение
CREATE POLICY audit_insert_only ON audit_log
FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);

4.4 ERD (упрощённая)

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

5. План реализации на 6 недель

Обзор спринтов

СпринтПериодЦельKey DeliverableSprint 1Нед. 1–2Foundation & InfraEvent bus, base schema, CI/CDSprint 2Нед. 2–3Connector Framework3 reference connectors (Email, Slack, Teams)Sprint 3Нед. 3–4Storage & EncryptionRLS, KMS, field-level enc, S3Sprint 4Нед. 4–5Sync EngineOffline cache, delta sync, conflict resolutionSprint 5Нед. 5–6Plugin SDK & APIWASM sandbox, SDK v1, public APISprint 6Нед. 6HardeningPen test, load test, runbook, GDPR

Sprint 1 — Foundation & Infra (Нед. 1–2)

Цель: Минимальная сквозная инфраструктура.

ЗадачаПриоритетРезультатRedis Streams: топики, consumer groups, DLQP0Event bus функционируетPostgreSQL: base schema + RLS policies + Flyway миграцииP0DB с изоляцией тенантовAPI Gateway (Kong / Caddy + JWT middleware)P0AuthN / AuthZ работаютUnified Event Schema v1.0 (JSON Schema + ajv)P0Schema зафиксирована и версионированаCI/CD pipeline (GitHub Actions: lint → test → docker build → staging deploy)P1Автоматизированный деплойMonitoring (Prometheus + Grafana: event lag, error rate, p99 latency)P1Observability с day oneБазовый Normalization Engine (raw.events → validate → map → normalized.events)P1Сквозной pipeline

DoD: Событие, опубликованное в raw.events, появляется в normalized.events через < 200ms. RLS проверена integration-тестом.

Sprint 2 — Connector Framework (Нед. 2–3)

Цель: Адаптерная модель + 3 reference connectors.

ЗадачаПриоритетРезультатConnectorRegistry + BaseConnector interface (TypeScript/Python)P0Расширяемый registryEmailConnector (IMAP + SMTP, OAuth2 для Gmail / Outlook)P0Получение emailSlackConnector (Events API + Socket Mode)P0Slack события нормализуютсяTeamsConnector (Microsoft Graph API webhooks)P1Teams события нормализуютсяDedup Engine: bloom filter в Redis + DB unique constraintP0Нет дублей при повторной доставкеRate limiter per connector (token bucket, configurable)P1API quota не превышаетсяError handling: retry policy (exponential backoff + jitter), DLQ routingP0Resilience при сбоях внешних API

DoD: Email, Slack, Teams события нормализуются и сохраняются без дублей. DLQ наполняется при симуляции ошибок.

Sprint 3 — Storage & Encryption (Нед. 3–4)

Цель: Безопасное хранение данных тенантов.

ЗадачаПриоритетРезультатKMS интеграция (AWS KMS primary / HashiCorp Vault fallback)P0KEK управляется централизованноEncryption Service: envelope encrypt/decrypt, DEK per tenantP0Данные шифруются при записиField-level шифрование body, from/to_addresses, storageRefP0PII защищён в покоеS3-compatible storage: upload, presigned URLs, CDN deliveryP1Вложения работаютKey rotation workflow (автоматический, zero-downtime dual-key period)P1Ротация без простояInbox Service: REST CRUD тредов, сообщений, labels (OpenAPI spec)P0Основной APIFull-text search: PostgreSQL tsvector (fallback Meilisearch при росте)P1Поиск по сообщениям

DoD: Зашифрованные сообщения читаются авторизованным пользователем; cross-tenant isolation тест проходит; ротация ключей выполняется без downtime.

Sprint 4 — Sync Engine (Нед. 4–5)

Цель: Offline-first клиент с надёжной синхронизацией.

ЗадачаПриоритетРезультатSync Service: delta sync по cursor (Redis, TTL = 7d)P0Клиент получает только diffVector clock для device-level conflict resolutionP0Конфликты разрешаются детерминированноClient offline cache: IndexedDB (web) / SQLite (mobile)P0Работа без сетиWebSocket push: real-time events на клиент (per-user channel)P0Мгновенные уведомленияConflict resolution strategy: server-wins + UI notification about conflictP1Пользователь информированBackground sync: Service Worker (web) / WorkManager (Android)P1Незаметная фоновая синхронизацияSync observability: consumer lag dashboard, stale cursor alertsP2Операционная видимость

DoD: Клиент без сети работает с кешем; после восстановления получает только delta-изменения; симуляция конфликта показывает корректное разрешение.

Sprint 5 — Plugin SDK & Public API (Нед. 5–6)

Цель: Расширяемость системы и открытый API.

ЗадачаПриоритетРезультатPlugin SDK v1: BaseConnector WASM interface + capability whitelistP0SDK задокументированWASM sandbox (Wasmtime): memory limit 64MB, CPU timeout 500msP0Изолированное выполнение плагинаPlugin Registry: загрузка, версионирование, health check, rollbackP0Плагины управляютсяPlugin manifest.json: permissions, rate limits, schema, code signingP1Явные capabilitiesReference plugin: TelegramConnector (эталонная реализация для разработчиков)P1Пример для экосистемыPublic REST API v1: OpenAPI spec + API keys + per-key rate limitingP0Внешние интеграции готовыDeveloper portal: SDK docs, plugin publishing flow, changelogsP2Ecosystem-ready

DoD: Сторонний разработчик пишет коннектор-плагин по SDK и загружает его без изменений ядра; WASM isolation проверена fuzzing-тестом.

Sprint 6 — Hardening (Нед. 6)

Цель: Production-ready качество.

ЗадачаПриоритетРезультатPenetration testing: OWASP Top 10, tenant isolation bypass, SSRFP0Security report + закрытые findingsLoad testing: 10 K событий/с, latency p99 < 500ms (k6 / Locust)P0Performance baseline задокументированChaos engineering: отказ Redis, PostgreSQL failover, KMS недоступенP1SLA подтверждён экспериментальноRunbook: операционные процедуры, incident response, escalation pathsP0On-call готов к дежурствуAPI documentation: Swagger UI / Redoc, example requestsP0Docs completeGDPR compliance: data deletion (crypto-shredding), data export (DSR)P1Compliance audit passedDependency security audit (Snyk / Trivy): CVE-free baselineP1Нет критических уязвимостей

DoD: Прошёл pen test, нагрузочное и chaos тестирование; runbook задокументирован и пройден drill; GDPR deletion верифицирован.

6. Технические риски и Mitigation

#РискВероятностьImpactMitigationR-01Schema evolution ломает существующих потребителейСредняяВысокийSemantic versioning схемы; только additive changes в минорных версиях; contract testing (Pact) между producer и consumerR-02Rate limiting внешних API (Gmail: 250 quota units/user/s, Slack: 50 req/min)ВысокаяСреднийToken bucket per connector; jittered exponential backoff; приоритизация очереди; алерт при достижении 80% квотыR-03Утечка данных между тенантами через SQL-инъекцию или ошибку ORMНизкаяКритическийRLS как last-resort барьер; parameterized queries обязательны; автоматизированные cross-tenant isolation тесты в CI; ежеквартальный pen testR-04Потеря DEK при сбое KMS → данные недоступныНизкаяКритическийMulti-region KMS replicas; зашифрованный DEK backup в отдельном хранилище; runbook восстановления; ежеквартальный DR drillR-05Конфликты данных при offline sync — пользователь теряет данныеСредняяВысокийСохранение обеих версий; UI уведомление о конфликте с возможностью manual resolution; полный event log для replayR-06Вредоносный WASM плагин — DoS или memory leakСредняяВысокийMemory cap 64MB per plugin; CPU timeout 500ms; capability whitelist; обязательное code signing; плагины проходят security review перед публикациейR-07Redis Streams — потеря сообщений при падении до ACKСредняяВысокийConsumer group + XACK только после успешной обработки; DLQ для failed messages; WAIT команда для durability; мониторинг consumer lagR-08GDPR right-to-erasure — сложность удаления зашифрованных данныхСредняяСреднийCrypto-shredding: уничтожение DEK делает ciphertext недоступным; дополнительно hard delete для plaintext полей; audit trail удаления хранится отдельноR-09Vendor lock-in на облачный KMSСредняяСреднийАбстракция KMSProvider interface; поддержка HashiCorp Vault (self-hosted) как fallback с первого дняR-10Деградация full-text search при росте БД (>100M строк)СредняяСреднийtsvector индекс + периодический REINDEX; при >100M строк — выделенный Meilisearch; партиционирование по tenant_id + received_at

7. Приложения

A. Connector Adapter Interface (Pseudocode)

typescriptinterface ConnectorManifest {
sourceType: string
version: string
capabilities: Array<'read' | 'send' | 'webhook'>
rateLimits: { requestsPerSecond: number }
requiredPermissions: string[]
}

interface BaseConnector {
readonly sourceType: string
readonly manifest: ConnectorManifest

authenticate(credentials: EncryptedCredentials): Promise<AuthContext>
fetchEvents(cursor: SyncCursor): AsyncIterator<RawEvent>
handleWebhook?(payload: unknown): RawEvent | null
sendMessage?(draft: MessageDraft): Promise<ExternalId>

onError(error: ConnectorError): RetryPolicy
healthCheck(): Promise<HealthStatus>
}

B. Plugin Manifest Schema

json{
"pluginId": "com.example.telegram-connector",
"version": "1.2.0",
"sourceType": "plugin:telegram",
"capabilities": ["read_messages", "send_messages"],
"requiredPermissions": ["network.api.telegram.org", "storage.read"],
"rateLimits": { "requestsPerSecond": 30 },
"wasmModule": "connector.wasm",
"checksum": "sha256:a3f5c2..."
}

C. Deployment Topology (Production)

Kubernetes Cluster:
API Gateway — 2+ pods, HPA (CPU 60%)
Inbox Service — 3+ pods, HPA
Sync Service — 3+ pods, stateless, HPA
Normalization Engine — 3+ pods, HPA (consumer lag-based)
Connector Runner — per-connector Deployment, restartPolicy: Always
Encryption Service — 2+ pods (low latency SLA, no aggressive HPA)
Plugin Registry — 2+ pods

Data:
PostgreSQL — Primary + 2 Read Replicas + PgBouncer
Redis Cluster — 3 shards × 2 replicas
S3 — Multi-region replication, versioning ON
KMS — AWS KMS multi-region OR Vault HA cluster

D. Key Metrics & SLOs

МетрикаTargetEvent pipeline latency (raw → normalized)p99 < 500msAPI Gateway response timep99 < 200msOffline sync delta delivery< 5s after reconnectMessage dedup false-negative rate< 0.001%Encryption/decryption overhead< 5ms per fieldUptime (API Gateway + Inbox Service)99.9% monthlyRTO (Recovery Time Objective)< 30 minRPO (Recovery Point Objective)< 5 min

Документ подготовлен в рамках технического RFC. Все ADR требуют ревью команды перед финализацией архитектуры.

### Шаг 6: Design System (Claude)

Промпт:

Ты дизайн-директор и senior UI engineer. Сделай дизайн-концепт и UI spec для secure unified inbox web app.

Стиль:

- Профессиональный, спокойный, high-trust.
- Отличная читаемость, ясная иерархия.
- Без кричащих цветов и без визуального шума.

Сделай:

1. Design tokens: color, typography, spacing, radius, shadows.
2. Компоненты: inbox item, source badge, priority badge, thread panel, command palette, security card.
3. Состояния: hover/focus/disabled/error/loading/skeleton.
4. Адаптив: desktop/tablet/mobile.
5. Accessibility: WCAG AA.
6. Итог: React + Tailwind UI snippets (только ключевые компоненты).

Ограничение:

- Дизайн должен соответствовать privacy-first идее (не провоцировать лишний сбор данных).

#### Ответ агента (вставь сюда)

---

## 3) Как присылать ответы мне

После каждого шага присылай мне:

1. Название шага (например: "Шаг 2 Security Architect").
2. Полный ответ агента.
3. Если есть спорные моменты, добавь список вопросов.

Я в ответ:

- Нормализую результат.
- Укажу противоречия.
- Объединю в единую спецификацию.
- Дам следующий точный шаг.

---

## 4) Критерий готовности к старту кодинга

К коду переходим только если выполнено все:

1. Согласован Product Scope MVP.
2. Утвержден Security Baseline (P0 закрыты).
3. Утверждена Integration Matrix (Wave 1 выбран).
4. Утверждены UX-флоу и IA.
5. Утверждена техническая архитектура и ADR.

Если хотя бы 1 пункт не закрыт — код не начинаем.
