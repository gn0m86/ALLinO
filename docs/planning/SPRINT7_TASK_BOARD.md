# ALLinO Sprint 7 Task Board

Статус: Closed (S7-01, S7-04 done; S7-02/S7-03 explicitly deferred by user decision, see below)
Дата старта: 2026-07-01
Длительность: не оценивается по дням — задачи закрываются по одной, с тестами и обновлением CURRENT_STATE.md.

## Цель спринта

Sprint 1-6 закрыли breadth (9 коннекторов, Wave 1 + Wave 2) и большую часть security-gate P0 списка
(rate limiting, security headers, encryption at rest, Vault-backed secrets, JWT tenant binding, event-bus
external worker + DLQ — все подтверждены по коду в PROJECT_REVIEW_2.md follow-up).

Sprint 7 не открывает Wave 3. Это explicitly a hardening/cleanup sprint для того, что осталось открытым
после двух раундов ревью (`PROJECT_REVIEW.md`, `PROJECT_REVIEW_2.md`) и не было ни на одном борде.

## Правила работы

1. Никаких новых интеграций (Wave 3) — не в scope этого спринта.
2. Каждая задача закрывается с тестами + записью в CURRENT_STATE.md.
3. Деструктивные действия (drop table, необратимые миграции схемы) — только после явного подтверждения
   пользователя, даже если задача формально "in progress" на этом борде.

---

## Board (состояния)

### Ready

- [ ] (нет активных задач — см. "Deferred" ниже)

### In Progress

- [ ] (нет активных задач)

### Done

- [x] S7-01 JWT algorithm hardening: support RS256 (asymmetric) verification, not just HS256.
- [x] S7-04 Security Center + Settings core-shell views, plus a frontend CSP bug found and fixed while
      verifying them in a real browser.

### Deferred (explicit user decision, 2026-07-01)

- [ ] S7-02 Postgres + real Row-Level Security path. User decision: not needed until there's a real
      multi-tenant production deployment with untrusted-tenant data; SQLite stays as-is for now. Re-open
      when a production/multi-tenant cutover is actually being planned — don't start this speculatively.
- [ ] S7-03 Fate of `threads`/`users` tables (drop vs. repurpose). User decision: leave as-is — documented
      as deprecated (`0009_deprecate_threads_users.sql`), not dropped. Revisit only if a real requirement
      needs a user-record model or thread-table shape shows up.

### Blocked

- [ ] (блокеры и зависимости)

---

## S7-01 — JWT RS256 support

Why: `PROJECT_MASTER_BRIEF.md` P0 list (`BE-01`) specifies `RS256 only; reject alg:none, HS256`. Current
implementation only supported HS256 (shared-secret) verification. This service only ever *verifies* JWTs
issued by an external IdP — it never issues them — so what's actually needed is public-key verification
support, not a private key here.

DoD:

- `ALLINO_JWT_ALGORITHM` can be set to `RS256` (or any `RS*`/`ES*`/`PS*` asymmetric alg).
- New config `ALLINO_JWT_PUBLIC_KEY` (PEM string) used as the verification key for asymmetric algorithms;
  `ALLINO_JWT_SECRET` remains the verification key for symmetric (`HS*`) algorithms — no behavior change
  for existing HS256 deployments.
- `core/security.py` picks the correct key material based on algorithm family instead of assuming a shared
  secret.
- Tests cover: valid RS256 token accepted, tampered/invalid-signature RS256 token rejected, existing HS256
  tests unaffected.

---

## S7-04 — Security Center + Settings core-shell completion

Why: `CLAUDE.md` §6 requires 5 core shell views (Inbox, Focus, Incident, Security Center, Settings). Only 3
existed; "Security Center" and "Settings" were nav buttons with no click handling — dead buttons, the same
pattern previously fixed for Focus/Incident mode.

DoD:

- `Security Center` renders the tenant-scoped audit log (existing, previously-unused-by-frontend
  `GET /api/v1/ingestion/audit` endpoint) with loading/error-retry/empty states.
- `Settings` shows tenant id, backend URL, and per-connector configuration status, read-only (no fake
  editable secrets — those stay env/Vault-only).
- Verified live in a browser (Playwright MCP), not just `next build` — this is how a real, previously
  undiscovered CSP bug was caught (see below).

Bonus finding: the frontend's `Content-Security-Policy` (from an earlier session's security-headers work)
was `default-src 'self'` with nothing else — this silently broke Google Fonts, every inline `style={{}}`
(used by every component in this app), Next.js's own inline scripts, and cross-origin `fetch()` to the
backend. Fixed in `next.config.mjs` with policy directives that actually match what this app does.

---

## Sprint 7 Exit Criteria

1. S7-01 closed with tests and doc update — done, see CURRENT_STATE.md.
2. S7-02 and S7-03 explicitly deferred by user decision on 2026-07-01 (asked directly, user picked the
   conservative default for both) — not abandoned, just consciously not in scope until their trigger
   condition above is met.
3. S7-04 closed: core shell now matches CLAUDE.md §6 spec; frontend CSP regression fixed and verified live
   in a browser. Sprint 7 is closed with this outcome.
