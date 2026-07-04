# ALLinO Sprint 8 Task Board

Статус: Closed (S8-01 done)
Дата старта: 2026-07-01
Длительность: не оценивается по дням — задачи закрываются по одной, с тестами и обновлением CURRENT_STATE.md.

## Цель спринта

Sprint 7 закрыл JWT RS256 hardening и core-shell completion (Security Center + Settings). Sprint 8
продолжает тот же hardening/cleanup трек: закрывает оставшийся применимый P1-пункт security baseline
(`PROJECT_MASTER_BRIEF.md` §4) — BE-09 sanitized error responses — который ещё не был на борде.

Не в scope: Wave 3 интеграции, инфраструктурные P1/P2 пункты, требующие внешней инфраструктуры,
которой у проекта нет (WAF, SIEM, mTLS service mesh, DDoS protection, DNSSEC) — они не применимы к
текущей архитектуре (local-first, single backend service, no mesh/edge layer) и не открываются без
отдельного явного решения.

## Правила работы

1. Каждая задача закрывается с тестами + записью в CURRENT_STATE.md.
2. Деструктивные действия — только после явного подтверждения пользователя.

---

## Board (состояния)

### Ready

- [ ] (нет)

### In Progress

- [ ] (нет)

### Done

- [x] S8-01 BE-09: Sanitized error responses (generic error + error_id, no leaked internals)

### Blocked

- [ ] (нет)

---

## S8-01 — Sanitized error responses (BE-09)

Why: `PROJECT_MASTER_BRIEF.md` P1 `BE-09` requires prod error responses to be generic with an
`error_id` for internal correlation, with stack traces only in internal logs. All existing `HTTPException`
raises in the codebase already use hand-written safe messages, but there is no global handler for
*unhandled* exceptions — currently they'd fall through to Starlette's bare default response with no
correlation id for matching a client-visible error to server-side logs.

DoD:

- Global exception handler registered on the FastAPI app for unhandled exceptions.
- Response body: generic message + `error_id` (UUID), no exception internals/stack trace in the response.
- Full exception detail + `error_id` logged server-side (internal logs only).
- Existing `HTTPException` responses unaffected (still return their specific status/detail).
- Test coverage: unhandled exception path returns sanitized body with `error_id`; existing HTTPException
  paths still behave as before.

---

## Sprint 8 Exit Criteria

1. S8-01 closed with tests and CURRENT_STATE.md changelog entry — done. Backend: `pytest -q` => 157
   passed; `ruff check app tests --select F,E9` => all checks passed.
