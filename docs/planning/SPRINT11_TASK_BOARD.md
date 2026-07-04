# ALLinO Sprint 11 Task Board

Статус: Closed (S11-01, S11-02 done)
Дата старта: 2026-07-01

## Цель спринта

`PROJECT_MASTER_BRIEF.md`: "Ответы (reply/action) не входят в P0, добавляются поэтапно после
security-gate". Security-gate по факту закрыт (Sprint 1-9). Приложение на данный момент полностью
read-only — ни бэкенд, ни фронтенд не имеют ни одного пути записи наружу (подтверждено grep'ом:
0 совпадений на "reply"/"send_message"/"outbound" в backend, фронтенд содержит только статичный
UI-placeholder в `ThreadPanel.tsx`, без обработчика).

Пользователь выбрал это направление явно (после Generic HTTP Connector в Sprint 10).

## Scope decision (важно)

`CLAUDE.md` §2 не допускает "full write-back across all sources" в v1. Поэтому MVP этого спринта —
**не все источники**, а только два, у которых:
1. Простой bot-token API для отправки сообщения (никакого OAuth-флоу).
2. `external_id`, уже сохранённый в `messages.external_id`, содержит всё нужное для адресации ответа
   без дополнительного хранения сырого payload (Telegram: `chat_id:message_id`; Slack: `channel:ts`).

Это Telegram и Slack. GitHub/GitLab/Jira "ответ" — это комментарий к issue/PR, другая модель данных
(нужен номер issue, не просто "reply в тред") — сознательно вне scope, отдельная задача при
необходимости.

## Правила работы

1. Каждая задача — с тестами + записью в CURRENT_STATE.md.
2. Секреты (bot tokens) не добавляются новые — переиспользуются уже существующие
   `ALLINO_TELEGRAM_BOT_TOKEN` / `ALLINO_SLACK_BOT_TOKEN` (уже в `.env.example` для poll-пути).
3. Frontend composer в `ThreadPanel.tsx` — реально wire-up, не просто backend API. UI-заглушка
   "Reply securely… / End-to-end encrypted" уже существует, но кнопка Send ничего не делает и текст
   вводить некуда (statичный div, не textarea). Обязательна живая проверка в браузере
   (CLAUDE.md §6) — прошлый CSP-баг и Sprint 9 HMR-ловушка найдены только так.
4. Копия "End-to-end encrypted" в UI **не соответствует действительности** — это HTTPS до бэкенда +
   исходящий HTTP-запрос к Telegram/Slack Bot API, не E2E-шифрование содержимого. Будет исправлена на
   честную формулировку при wiring — это не opinion-правка стиля, а security-first принцип
   (не показывать пользователю неверную гарантию безопасности).

---

## Board

### In Progress

- [ ] (нет)

### Done

- [x] S11-01 Backend: reply delivery (Telegram + Slack), audit trail, permission tier
- [x] S11-02 Frontend: wire ThreadPanel composer to the reply endpoint (+ found and fixed a pre-existing
      hydration bug in `page.tsx` while verifying live, see below)

---

## S11-01 — Backend reply delivery

DoD:

- Новая таблица `outbound_replies` (миграция `0011_outbound_replies.sql`): id, tenant_id, event_id,
  source, external_id, text (encrypted), status (sent/failed), error (encrypted), created_at.
- `messages_repo.get_message(tenant_id, event_id)` — точечный lookup (раньше был только list).
- `connectors/telegram_connector.py` добавляет `send_telegram_reply(token, external_id, text)` —
  Bot API `sendMessage`, парсит `chat_id:message_id` из `external_id`, `reply_to_message_id` когда есть.
- `connectors/slack_connector.py` добавляет `send_slack_reply(token, external_id, text)` — Web API
  `chat.postMessage`, парсит `channel:ts`, отвечает в тред через `thread_ts`.
- Новый permission tier `require_reply_permission` в `core/security.py` (тот же паттерн, что
  `require_connector_sync_permission`), конфиг `ALLINO_JWT_REPLY_ROLES`/`ALLINO_JWT_REPLY_SCOPES` в
  `core/config.py`.
- `POST /api/v1/ingestion/messages/{event_id}/reply` — tenant-scoped, отклоняет неизвестный event_id
  (404), неподдерживаемый source (400), отсутствующий bot token (503, fail-closed), ошибку доставки
  (502). Успех/неудача пишутся и в `outbound_replies`, и в `audit_logs` (append-only).
- `GET /api/v1/ingestion/replies` — tenant-scoped список отправленных ответов (операционная видимость,
  тот же паттерн что `connector_runs`).
- Тесты: парсинг external_id для обоих источников, успешная отправка (mocked HTTP), ошибка API,
  неподдерживаемый source, чужой tenant не видит/не может ответить на чужое сообщение, audit-запись
  создаётся.

## S11-02 — Frontend composer wiring

DoD:

- `ThreadPanel.tsx`: статичный div заменён на controlled `<textarea>`, кнопка Send реально отправляет
  `POST /messages/{event_id}/reply` через новый `sendReply()` в `lib/api.ts`.
- Composer виден только когда `item.source` поддерживает reply (`telegram`/`slack`) — иначе честное
  disabled-состояние с объяснением, а не молчаливая заглушка.
- Loading/error/success состояния (мандаторно по CLAUDE.md §6 — error и empty states обязательны).
- "End-to-end encrypted" заменено на точную формулировку.
- Проверено вживую в браузере (production build, см. урок Sprint 9 про dev-server HMR в этой
  песочнице) — реальная отправка через seeded/test backend, скриншот перед закрытием.

---

## Sprint 11 Exit Criteria

1. S11-01 и S11-02 закрыты с тестами и записью в CURRENT_STATE.md — done.
2. Полный backend test suite зелёный (191 passed), `ruff check --select F,E9` чист, `pip-audit` чист.
3. Frontend: `tsc --noEmit` чист, `npm run build` успешен, `npm audit` чист (0 vulnerabilities), живая
   проверка в браузере (production build) — Inbox → Telegram-сообщение → композер → отправка → честная
   503-ошибка "not configured" корректно показана в UI; disabled-состояние для GitHub корректно;
   Security Center показывает audit-трейл.
4. Явно вне scope: reply для GitHub/GitLab/Jira/Linear/Discord/Zoom/Teams (другая модель данных);
   автоматическое повторное появление отправленного reply как нового inbox-сообщения (не требуется
   для MVP, отдельное решение при необходимости).
5. Найдено и исправлено попутно (не было в исходном scope, но всплыло при обязательной живой проверке
   в браузере — тот же паттерн, что CSP-баг в Sprint 7): `frontend/src/app/page.tsx` читал
   `sessionStorage` синхронно в `useState`-инициализаторах `mode`/`filters`, что вызывало React
   hydration error #418 для вернувшегося пользователя (SSR всегда рендерит default, клиент на первом
   рендере — persisted-значение, если оно отличается от default). Исправлено: инициализаторы теперь
   всегда возвращают SSR-safe default, восстановление персистентного состояния перенесено в
   mount-only `useEffect` (после гидратации). Проверено воспроизведением (`sessionStorage.setItem`
   вручную перед reload) и подтверждением отсутствия ошибки после фикса.
