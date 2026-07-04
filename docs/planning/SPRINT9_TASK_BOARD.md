# ALLinO Sprint 9 Task Board

Статус: Closed (S9-01 done)
Дата старта: 2026-07-01
Длительность: не оценивается по дням — задачи закрываются по одной, с тестами и обновлением CURRENT_STATE.md.

## Цель спринта

Продолжение hardening-трека (Sprint 7, Sprint 8). `PROJECT_MASTER_BRIEF.md` §4 P1 `OP-04` требует
CI/CD security gates (SAST/SCA), которых в проекте не было ни на одном борде. При подготовке gate
`pip-audit` (dry-run) нашёл реальные CVE в зависимостях, включая PyJWT — библиотеку, на которой
держится вся модель аутентификации приложения. Это подняло вопрос выше уровня "просто добавить CI
шаг": сначала нужно закрыть текущие находки, потом включать gate.

Пользователь выбрал вариант "полное исправление сейчас": обновить fastapi+starlette, pyjwt,
cryptography, прогнать полный набор тестов, закрыть найденные CVE, и только затем подключить
pip-audit / npm audit как обязательную проверку в CI.

## Правила работы

1. Каждая задача закрывается с тестами + записью в CURRENT_STATE.md.
2. Деструктивные действия — только после явного подтверждения пользователя.

---

## Board (состояния)

### In Progress

- [ ] (нет)

### Done

- [x] S9-01 OP-04: Dependency remediation (fastapi/starlette, pyjwt, cryptography, next.js) + pip-audit/npm audit CI gate

---

## S9-01 — Dependency vulnerability remediation + SCA CI gate (OP-04)

Why: `pip-audit` dry-run against `backend/requirements.txt` found 25 known vulnerabilities across 3
packages: `pyjwt==2.9.0`, `cryptography==43.0.3`, and `starlette==0.38.6` (transitive via
`fastapi==0.115.0`). PyJWT sits directly under this app's entire auth model (API key / JWT bearer
verification, RS256 support added in Sprint 7), so this isn't a routine bump.

DoD:

- `fastapi`, `uvicorn`, `pydantic`, `httpx`, `PyJWT`, `redis`, `cryptography` bumped to current patched
  versions in `backend/requirements.txt`.
- Full backend test suite passes after the bump (no silent behavior change in auth/JWT/encryption
  paths).
- `pip-audit -r backend/requirements.txt` reports zero known vulnerabilities.
- `backend-ci.yml` runs `pip-audit` as a required step (fails the build on findings).
- Frontend: `npm audit` reviewed; `frontend-ci.yml` runs `npm audit --audit-level=high` as a required
  step.

---

## Sprint 9 Exit Criteria

1. S9-01 closed with tests, clean `pip-audit`/`npm audit` gates in CI, and CURRENT_STATE.md changelog
   entry — done. Backend: `pytest -q` => 157 passed; `pip-audit -r backend/requirements.txt` => no known
   vulnerabilities. Frontend: `tsc --noEmit` clean; `npm run build` => success; `npm audit
   --audit-level=high` => 0 vulnerabilities. Also found (while remediating) that `next@14.2.25` itself had
   a high-severity advisory set open; bumped to `16.2.9` (see note below) since fixing the transitive
   `postcss` finding required it anyway.
