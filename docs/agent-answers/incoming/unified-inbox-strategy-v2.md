# Unified Inbox — Product Strategy v2
> Local-first · Free APIs only · No vendor negotiations  
> Stack: Python FastAPI · React/Next.js · SQLite · Docker

---

## Ограничения как преимущества

| Ограничение | Как переформулировать |
|---|---|
| Нет партнёрских API | "Работает с твоим PAT — никаких корпоративных согласований" |
| Данные только локально | "Твои уведомления не уходят ни в какое облако" |
| Open source / self-hosted | "Ставишь через Docker за 2 минуты и владеешь всем" |
| Только открытые API | "Работает там, где разработчик и так уже есть" |

---

## 1. ICP-сегменты

| Сегмент | Размер | Стек | WTP |
|---|---|---|---|
| Indie Developer / Freelancer | 1 | GitHub, GitLab, Telegram, Linear | $0 (self-hosted) → $6–10/мес cloud |
| Privacy-conscious Engineer | 1–5 | GitHub, GitLab, Discord, Jira | self-hosted, donate / sponsor |
| Small Remote Team (no IT dept.) | 5–15 | GitHub + Linear + Telegram + Discord | $10–20/мес/seat |
| DevOps / Platform Engineer | any | GitLab CI, GitHub Actions, Telegram alerts | self-hosted, enterprise later |

> **Сдвиг ICP относительно v1:** убираем корпоративных покупателей из Wave 1.  
> Наш первый пользователь — разработчик, который сам себе DevOps и сам платит.

### Топ-7 болей (скорректированы)

| # | Боль | Интенсивность | Частота |
|---|---|---|---|
| 1 | 8–12 вкладок одновременно: GitHub, GitLab, Telegram, Linear, Jira, Discord | 🔴 Критичная | Ежедневно |
| 2 | PR-ревью, упомянутый issue и Telegram-алерт — три разных приложения об одном событии | 🔴 Критичная | Несколько раз/день |
| 3 | Важный GitHub notification тонет среди Dependabot и CI-спама | 🔴 Критичная | Ежедневно |
| 4 | Нет связи issue ↔ PR ↔ сообщение в Telegram/Discord | 🟠 Высокая | Ежедневно |
| 5 | Все существующие инструменты агрегации требуют облачного доступа к токенам | 🟠 Высокая | Постоянно (доверие) |
| 6 | Context switching убивает flow — GitLab CI упал, надо открыть 4 источника | 🟠 Высокая | Ежедневно |
| 7 | Нет единой точки для stand-up: что я вообще делал вчера? | 🟡 Средняя | Ежедневно |

---

## 2. Job Stories

| # | Ситуация | Мотивация | Ожидаемый результат |
|---|---|---|---|
| JS-01 | Когда начинаю рабочий день | хочу видеть pending actions из GitHub, GitLab, Linear и Telegram в одном месте | планирую день за 3 минуты без открытия 6 вкладок |
| JS-02 | Когда вхожу в deep work | хочу отключить некритичные уведомления одним действием | работаю 90+ минут без прерываний |
| JS-03 | Когда мне назначен PR-ревью на GitHub | хочу видеть связанный Linear-issue и предыдущие комментарии прямо здесь | даю ревью без переключения контекста |
| JS-04 | Когда падает GitLab CI | хочу один алерт вместо трёх (email + Slack-бот + Telegram) | не собираю картину по трём каналам |
| JS-05 | Когда возвращаюсь после митинга | хочу быстро просмотреть что пропустил, отфильтровав по важности | возвращаюсь в работу за 5 минут |
| JS-06 | Когда настраиваю инструмент | хочу вставить PAT и через минуту видеть уведомления | не регистрирую OAuth-приложения и не жду одобрения |
| JS-07 | Когда думаю об использовании инструмента | хочу чтобы мои токены и сообщения не уходили в чужое облако | могу подключить рабочие аккаунты без параноии |
| JS-08 | Когда on-call | хочу чтобы critical Telegram-алерты были отделены от GitHub-шума | не пропускаю инциденты |
| JS-09 | Когда менеджер просит статус | хочу auto-summary активности по GitHub + Linear за последние 24ч | отвечаю за 30 секунд без ручного составления |
| JS-10 | Когда заканчиваю задачу | хочу снуз всех связанных уведомлений одним действием | не получаю алерты о закрытой теме |
| JS-11 | Когда хочу поставить коллеге | хочу скинуть docker-compose.yml и всё | коллега разворачивает за 2 минуты без инструкций |
| JS-12 | Когда работаю с двух машин | хочу синхронизацию read-статуса (опционально через свой сервер) | не читаю одно и то же дважды |

---

## 3. Топ-12 возможностей MVP + Анти-фичи

### Интеграции Wave 1 — только бесплатные API без переговоров

| Источник | Метод | Статус |
|---|---|---|
| **GitHub** | PAT или GitHub App (бесплатно) | ✅ Wave 1 |
| **GitLab** | Personal Access Token | ✅ Wave 1 |
| **Telegram** | Bot API (BotFather, 2 мин) | ✅ Wave 1 |
| **Linear** | API key в настройках | ✅ Wave 1 |
| **Jira** | API token (Atlassian account) | ✅ Wave 1 |
| **Discord** | Bot API (Developer Portal) | ✅ Wave 1 |
| Slack | требует workspace admin | 🟡 Wave 2 (только свой workspace) |
| Teams | Azure app registration | 🔴 Wave 3 (по demand) |

### MVP Features — приоритет по Value/Effort

| P | Фича | Value | Effort | Обоснование |
|---|---|---|---|---|
| P0 | PAT-based подключение: GitHub, GitLab, Telegram, Linear, Jira | Core | S | Никаких OAuth-серверов, работает сразу |
| P0 | Read-only агрегация в локальный SQLite | Core | M | Данные не уходят никуда — это фича |
| P0 | Smart deduplication (одно событие → одна карточка) | Core | M | Убивает боль #2 |
| P1 | Priority classifier rule-based (тип + источник + ключевые слова) | High | S | Решает боль #3 без AI |
| P1 | Thread context stitching: GitHub issue ↔ PR ↔ Telegram-алерт | High | L | Главный дифференциатор |
| P1 | Focus Mode / DND с расписанием | High | S | Решает боль #6 |
| P1 | Keyboard-first навигация + command palette | High | S | Developer UX, high NPS driver |
| P2 | Universal search по всем источникам (локальный FTS в SQLite) | Medium | M | Всё на месте, никаких cloud search API |
| P2 | Snooze / defer уведомлений | Medium | S | Стандарт для inbox-продуктов |
| P2 | Custom notification rules / filters | Medium | M | Решает боль #5 |
| P2 | Read status sync across devices | Medium | S | Через свой сервер или без (single-device MVP) |
| P3 | Daily activity digest (для stand-up) | Low-Med | S | Решает боль #7, генерируется локально |

### Анти-фичи MVP

| Анти-фича | Почему нет |
|---|---|
| ❌ Write-back / ответы из inbox | Расширяет scope PAT → бо́льшая поверхность атаки |
| ❌ Облачное хранение токенов | Главный страх пользователя. Токены только локально |
| ❌ AI через внешний API (OpenAI и т.д.) | Отправка рабочих данных наружу — contra privacy-first |
| ❌ 10+ интеграций сразу | Глубина важнее ширины. 5–6 идеальных > 12 сырых |
| ❌ Team analytics / dashboards | Другой ICP, другой продукт |
| ❌ Browser extension | Расширенный DOM-доступ нарушает security-first позицию |
| ❌ Electron (в пользу Tauri) | Electron: ~200 MB, Tauri: ~15 MB — важно для self-hosted |

---

## 4. Метрики успеха

> Продукт self-hosted/open-source → метрики иные, чем у SaaS

### 30 дней — Validation Metrics

| Метрика | Цель | Инструмент |
|---|---|---|
| GitHub stars | ≥ 200 | GitHub Insights |
| Docker Hub pulls | ≥ 500 | Docker Hub stats |
| Activated installs (≥2 интеграции подключены) | ≥ 40% от pulls | Opt-in телеметрия / GitHub Discussions |
| Setup time (fork → первое уведомление) | < 5 мин | User testing (5 человек) |
| Issues opened (bug vs feature request ratio) | < 30% bugs | GitHub Issues |
| Discord/Telegram community joins | ≥ 100 | Community stats |

### 90 дней — Retention & Monetization Signals

| Метрика | Цель | Инструмент |
|---|---|---|
| GitHub stars | ≥ 1 000 | GitHub Insights |
| Active installs (weekly pull от Docker) | ≥ 300 | Docker Hub |
| Sponsor / donation conversion (GitHub Sponsors) | ≥ 1–2% активных | GitHub Sponsors |
| Community contributors (PRs от не-авторов) | ≥ 5 | GitHub |
| Cloud-hosted waitlist signups | ≥ 150 | Лендинг + форма |
| NPS (Discord/Telegram опрос) | ≥ 45 | Manual survey |

---

## 5. Роадмап — 3 Волны

### Wave 1 — Foundation (Месяцы 1–3)
**Тема: "Your notifications. Your machine. Your rules."**

| # | Фича | Цель |
|---|---|---|
| W1-01 | PAT-интеграции: GitHub, GitLab, Telegram Bot, Linear, Jira | Сразу работает у 90% ЦА |
| W1-02 | Read-only агрегация → локальный SQLite | Local-first периметр |
| W1-03 | Smart deduplication | Убиваем боль #2 |
| W1-04 | Priority classifier (rule-based) | Signal vs noise |
| W1-05 | Thread context stitching (issue ↔ PR ↔ alert) | Главный дифференциатор |
| W1-06 | Focus Mode / DND | Deep work |
| W1-07 | Keyboard navigation + command palette | Developer UX |
| W1-08 | Docker Compose packaging + Web UI (Next.js) | Установка за 2 минуты |

**Стек:** Python FastAPI · Next.js · SQLite · Docker Compose  
**Exit criteria:** 200 GitHub stars · 500 Docker pulls · setup < 5 мин на cold test

---

### Wave 2 — Intelligence (Месяцы 4–6)
**Тема: "Smart, still local"**

| # | Фича | Цель |
|---|---|---|
| W2-01 | Discord Bot интеграция | Закрываем Discord-аудиторию |
| W2-02 | Slack (только свой workspace через Bot Token) | Частичное покрытие |
| W2-03 | Local AI classifier (Ollama / llama.cpp) | Умная приоритизация без утечки данных |
| W2-04 | Activity digest: локальный auto stand-up | Saves 10 min/day |
| W2-05 | Custom rules v2 (regex + advanced filters) | Power user retention |
| W2-06 | Snooze + defer + reminders | Workflow completion |
| W2-07 | Tauri Desktop App (замена Electron-обёртки) | Native, 15 MB vs 200 MB |
| W2-08 | Optional cloud sync (self-hosted backend, E2E encrypted) | Multi-device без vendor |

**Exit criteria:** 1 000 stars · 300 active installs · cloud waitlist ≥ 150

---

### Wave 3 — Monetization (Месяцы 7–12)
**Тема: "Free forever self-hosted. Pay for convenience."**

| # | Фича | Бизнес-цель |
|---|---|---|
| W3-01 | Cloud-hosted SaaS (managed, E2E encrypted) | Монетизация без потери privacy-позиции |
| W3-02 | Teams: shared inbox + shared rules | Расширение от 1 к команде |
| W3-03 | Teams, Zoom, PagerDuty (по demand из issues) | Enterprise coverage |
| W3-04 | Universal search v2 (semantic, локальный embeddings) | Power UX |
| W3-05 | Mobile app (React Native + локальный сервер) | On-call coverage |
| W3-06 | Plugin API для кастомных источников | Community integrations |
| W3-07 | GitHub Marketplace / VS Code extension | Distribution channel |

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

| Риск | Вероятность | Митигация |
|---|---|---|
| GitHub/GitLab меняют rate limits | Средняя | Webhook-first, polling как fallback |
| Пользователи не доверяют даже локальному хранению | Низкая | Open source = аудит кода, никакой телеметрии по умолчанию |
| Трудно монетизировать self-hosted | Высокая | Cloud tier с Day 1 как waitlist; open core модель |
| Сложность поддержки 6+ коннекторов | Средняя | Plugin архитектура с Wave 2, community берёт нишевые |
