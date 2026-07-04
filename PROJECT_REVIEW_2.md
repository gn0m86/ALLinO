# ALLinO — Project Review #2

Date: 2026-07-01
Scope: second-pass review, on top of `PROJECT_REVIEW.md` (review #1, same date). This file only — no other files were changed.

Context for this review: since review #1 was written, the project went from "Sprint 2 closed, 3 connectors" to "Sprint 6 closed, 9 connectors, JWT auth, event bus, cursor pagination, staging release-gate scripts" — all logged as having happened on 2026-07-01. That is an enormous amount of shipped surface area in one session. This review focuses on whether the *foundation* kept pace with the *breadth*, since that's the pattern most likely to hide problems: every sprint checklist says "GO", but each one only re-checks that sprint's own feature, never the cross-cutting security/architecture baseline from `CLAUDE.md` §4 and `PROJECT_MASTER_BRIEF.md`'s P0 list.

Overall verdict: **direction is right, pace is the risk.** Connector breadth (Wave 1 + Wave 2, all done) is ahead of schedule. The security gate and architecture baseline that CLAUDE.md calls "must not regress" have not regressed, but several of them were never actually implemented, and the sprint-closure process currently has no mechanism that would notice. Two of the findings below (tenant binding, insecure-by-default config) are things I'd fix before adding a 10th connector.

---

## 1. Critical findings (new since review #1)

### 1.1 Tenant isolation is caller-asserted, not credential-bound

[backend/app/core/tenant.py](backend/app/core/tenant.py#L4-L14) resolves `tenant_id` purely from the `X-Tenant-Id` header or `tenant_id` query param — a plain string, unchecked against the caller's identity.

There is exactly one shared `ALLINO_API_KEY` (or one JWT secret) for the whole deployment. Any caller holding that one key/token can put **any** tenant_id in the header and get full read/write access to that tenant's inbox, audit log, metrics, and connector registry. The repositories do filter `WHERE tenant_id = ?` correctly, but nothing upstream of that stops a caller from choosing which tenant's data to query.

This is not a hypothetical gap — it's explicitly called out as a P0 control in `PROJECT_MASTER_BRIEF.md` line 605 (`BE-05 Tenant Isolation: tenantId из JWT, не request` → "tenantId извлекается ТОЛЬКО из JWT claims"). The current implementation does the opposite of what the brief specifies: tenant_id comes from the request, never from JWT claims, and JWT payloads aren't even inspected for a tenant claim.

[backend/tests/test_tenant_isolation.py](backend/tests/test_tenant_isolation.py) only proves that two different `tenant_id` arguments passed directly to repo functions return disjoint rows — it never goes through the API/auth layer, so it can't catch this. There is no test anywhere that asserts "caller authenticated for tenant A cannot read tenant B by changing a header."

This was not flagged in review #1 because review #1 pre-dates JWT work; it became a live cross-tenant IDOR risk specifically once a shared JWT/API key started covering multiple tenants.

**Fix shape:** either embed tenant_id in the JWT claims and use that instead of the header (matches the brief), or, if header-based tenant selection must stay for the current single-key dev model, treat it explicitly as a known, documented limitation rather than "tenant isolation ✅" in the security gate.

### 1.2 "Fail-closed" auth is fail-open by default

`core/config.py` defaults:
```python
ALLINO_ENV: str = os.getenv("ALLINO_ENV", "development")          # config.py:39
ALLINO_ALLOW_INSECURE_DEV: bool = os.getenv(..., "true")          # config.py:43-45
```
`core/security.py`'s `require_api_key` only raises (503) when *both* no secret is configured *and* `ALLINO_ENV != "development"` *or* `ALLINO_ALLOW_INSECURE_DEV` is false. Both defaults point the same direction: insecure-allowed.

[docker-compose.yml](docker-compose.yml#L9-L13) — the one place meant to represent a "shared/prod-like" deployment — sets `ALLINO_ALLOWED_ORIGINS`, `ALLINO_DB_PATH`, and `ALLINO_API_KEY: "${ALLINO_API_KEY:-}"` (empty by default) but never sets `ALLINO_ENV` or `ALLINO_ALLOW_INSECURE_DEV`. So: `docker compose up` with no `.env` file gives you a fully open backend, silently, with zero warnings visible outside a log line.

CURRENT_STATE.md (2026-07-01 entry) describes this as "fail-closed when `ALLINO_API_KEY` is missing outside explicitly allowed local dev mode" — but "explicitly allowed" is the untouched default, not something an operator has to opt into. The security gate item is only as strong as its config defaults, and right now the defaults are exactly backwards from what "fail-closed" implies.

`test_api_key_security.py` only tests behavior when flags are monkeypatched to specific values — there's no test that imports `config.py` fresh with zero env vars set and asserts the resulting `require_api_key` behavior, so this gap has no regression coverage either.

**Fix shape:** flip the defaults (`ALLINO_ALLOW_INSECURE_DEV` default `false`; require explicit opt-in), or at minimum have `docker-compose.yml` set `ALLINO_ENV=production` so the compose path can't silently run insecure.

### 1.3 The "event bus" doesn't decouple anything — it's a synchronous round-trip

Review #1 §3.1 flagged: ingestion is fully synchronous inside the HTTP request, no queue, no backpressure. `CURRENT_STATE.md` (S3-04) reports this closed via `services/event_bus.py` with a Redis Streams path. Reading [event_bus.py](backend/app/services/event_bus.py#L48-L84): in `redis_stream` mode, the code does `xadd` for every event and then **immediately** `xrange`s each entry back out, in the same function call, then hands the same list to the same synchronous `processor`. There is no separate consumer, no worker process, nothing reads the stream asynchronously.

The Sprint 3 task board's own DoD for S3-04 lists "consumer worker baseline (local mode)" as part of the deliverable ([SPRINT3_TASK_BOARD.md:100](docs/planning/SPRINT3_TASK_BOARD.md#L100)) — that worker doesn't exist. What exists is Redis used as a write-then-immediately-read buffer inside one request, which adds latency and a new failure mode (network hop to Redis) without providing any of the actual benefit (async processing, backpressure relief, per-event retry, multiple consumers) that was the point of moving off synchronous processing in the first place.

`test_event_bus.py` only exercises the `direct` and `redis_fallback` (no-redis-installed) branches — nothing exercises the actual `redis_stream` branch, so this was never actually verified end-to-end even in the sense the code allows.

This one is worth being blunt about: it's the same architectural gap as review #1 §3.1, now wearing a checkbox that says "closed."

---

## 2. Security-gate items still open, now with 9 connectors sitting on top of them

CLAUDE.md §4 and `PROJECT_MASTER_BRIEF.md`'s P0 table ("до первого деплоя") both list these as must-have-before-shipping. Status after 6 sprints:

| Control | Brief ref | Status |
|---|---|---|
| Rate limiting (auth + ingestion) | BE-03, P0 | ❌ not implemented anywhere in `app/` (no slowapi/limiter, no middleware) |
| Encryption at rest | ST-01, P0 | ❌ SQLite plaintext file, no field/column encryption |
| CSP / HSTS headers | CL-01/CL-03, P0 | ❌ no security-headers middleware in `main.py`, nothing in frontend `next.config.mjs` |
| Secrets via Vault | BE-06, P0 | ❌ plain env vars only (`ALLINO_API_KEY`, `ALLINO_JWT_SECRET`, connector tokens) |
| MFA for admin paths | OP-02, P0 | ❌ no admin surface exists yet, so N/A in practice, but also not tracked as a gap |
| JWT hardening | BE-01 | ⚠️ partial — HS256 symmetric shared secret, not RS256; no `iss`/`aud` enforced unless explicitly configured (defaults to `verify_aud: False` when audience unset) |
| Append-only audit log | ST-05 | ✅ DB trigger (`0005_audit_append_only.sql`), tested |
| Tenant isolation | BE-05 | ❌ see §1.1 above |

None of these five ❌ rows appear as open items in `CURRENT_STATE.md`, in any `SPRINT*_TASK_BOARD.md`, or in any `RELEASE_HARDENING_CHECKLIST_S*.md`. That's the real process gap: every release checklist (S3 through S6) scopes itself to that sprint's own feature (e.g. S6's checklist only re-verifies Zoom/Teams), then declares "GO for continued delivery." None of them re-checks the CLAUDE.md §4 security gate as a whole. The gate can quietly stay broken indefinitely because nothing in the current process re-asks about it once a sprint's own DoD is met.

**Suggestion:** add one recurring section to every future release checklist — "Security Gate regression check" — that re-verifies the CLAUDE.md §4 list explicitly (even if the answer is "still open, tracked in X"), instead of only checking the sprint's own deliverable.

---

## 3. Residual / smaller findings

### 3.1 Connector token still accepted in JSON body, not just header

`CURRENT_STATE.md` (2026-07-01) says log sanitization + `X-Connector-Token` header closed the T-07 token-in-logs concern from review #1 §5.1. Looking at the actual endpoints (e.g. [ingestion.py:356-374](backend/app/api/ingestion.py#L356-L374)):
```python
connector_token = x_connector_token or payload.token
```
`payload.token` (the JSON body field) is still accepted as a fallback for every connector sync endpoint. The header path is additive, not a replacement — a caller (or an old client/script) can still send the token in the body, where it's more likely to be captured by API gateways, proxies, or request-logging middleware that logs bodies. Original concern is mitigated, not resolved.

### 3.2 Permission-dependency fallthrough is confusing, currently masked by router-level ordering

[security.py:112-113](backend/app/core/security.py#L112-L113) and the equivalent block in `require_ingestion_read_permission`:
```python
if not ALLINO_JWT_SECRET:
    return
```
Read literally: if JWT isn't configured, the function allows the request — regardless of whether an API key was even supplied or matched. This is safe **today** only because `require_api_key` is a router-level dependency ([ingestion.py:37-41](backend/app/api/ingestion.py#L37-L41)) that always runs first and already rejects unauthenticated callers before this function is reached. If anyone ever adds a new router/route that uses `require_connector_sync_permission` or `require_ingestion_read_permission` without also including `require_api_key`, it becomes a silent auth bypass. Worth a comment in the code (or a defensive re-check of the API key) so the safety property doesn't depend on remembering to wire two dependencies together correctly forever.

### 3.3 `threads` and `users` tables: still dead, now orphaned by design (not just unfinished)

Review #1 §3.3 flagged `users` and `connectors` as schema without repositories. `connectors` now has a real repo — good, closed correctly. `users` is still fully dead (confirmed: no repo, no references anywhere in `app/`).

`threads` (from `0001_init.sql`) is a new kind of problem: thread linking was subsequently implemented via `messages.thread_key` (migration `0007_thread_key.sql`) instead of via the `threads` table. So `threads` isn't merely "not yet implemented" — it's architecturally bypassed by a different mechanism that shipped later. Left as-is, a future agent reading the schema will reasonably assume `threads` is the thread-linking mechanism and either duplicate work or write to a table nothing reads. Worth an explicit decision: drop the table, or repurpose it, or add a one-line comment in the migration noting it's superseded by `thread_key`.

### 3.4 Postgres/RLS path is still a comment, six sprints later

`0002_rls.sql` is unchanged since review #1 — still just a commented-out example, SQLite remains the only real backend. That's a reasonable v1 scope call, but given `PROJECT_MASTER_BRIEF.md` lists `ST-03 Row-Level Security PostgreSQL` as a Sprint+1 (i.e. early) priority and CLAUDE.md §5 bakes "tenant_id + RLS" into the security gate description, it's worth either (a) explicitly deferring this in a dated planning note with a reason, or (b) putting a real Postgres migration on a sprint board before more features stack on top of the SQLite assumption (e.g. the new cursor pagination in `messages_repo.py` should be checked for SQLite-specific behavior that might not port cleanly).

---

## 4. Things review #1 flagged that are now genuinely fixed (verified against code, not just docs)

- Mode-based inbox filtering (`focus`/`incident` → priority filter) is real: [page.tsx:198-206](frontend/src/app/page.tsx#L198-L206) actually derives `filters` from `mode`, not just a label (review #1 §6.1 is closed).
- Wave 1 Core discrepancy (Jira/Telegram missing from Sprint 2, review #1 §4.1) is resolved — both shipped in Sprint 3 (S3-01, S3-02), confirmed in `CURRENT_STATE.md` and connector files exist with tests.
- `test_ingestion_idempotency.py`, `threads`-adjacent thread linking, error/empty states, frontend CI — all confirmed present and non-trivial, not just filenames.
- Test count claims are accurate: ran `pytest -q` directly → **110 passed**, matching the number in `CURRENT_STATE.md`'s last entry.
- Retry policy is genuinely HTTP-aware (429/5xx retry, fail-fast on other 4xx) with real endpoint-level tests (`test_zoom_connector.py`, `test_teams_connector.py` 401/429 scenarios) — solid, not just a checkbox.
- Connector registry + telemetry + run history (`connectors_repo.py`, `connector_runs_repo.py`) is well-built: tenant-scoped, has real upsert semantics, and the frontend actually renders it (`ConnectorOpsPanel.tsx`), not a stub.
- No secrets committed: checked for stray `.env` files — only `.env.example` files and a harmless `frontend/.env.local` (no real secrets, just local URLs), and `.gitignore` correctly excludes real env files and the SQLite DB.

---

## 5. Suggested next steps, in order

1. Decide the tenant-binding model explicitly (§1.1) before adding more connectors that read/write tenant data — this is the one item that turns into a real incident if missed, not just a checklist gap.
2. Flip the insecure-by-default config (§1.2) — smallest fix, biggest blast-radius reduction; currently one missing env var away from wide open in what's meant to be the shared/prod compose file.
3. Either implement a real async consumer for the event-bus path or stop calling it a start toward "Redis Streams as the event bus" in docs (§1.3) — right now it's misleading about what problem it solves.
4. Add rate limiting on auth/ingestion endpoints — it's explicitly P0 in the brief and currently has zero implementation, not partial.
5. Add a "security gate regression check" section to the release-checklist template so P0 items can't silently stay open sprint after sprint without at least being re-acknowledged.
6. Small cleanup when convenient: drop or repurpose `threads`/`users` tables, remove the `payload.token` body fallback once callers migrate to the header, add a comment to the permission-dependency fallthrough in `security.py`.

---

## 6. What's going well

The core engineering discipline is real, not just velocity: dedup via hash, tenant-scoped repo reads, append-only audit trigger with a test that actually tries to UPDATE/DELETE and expects failure, capability-matrix-driven frontend instead of hardcoded source lists, connector contract tests per-provider, and CI running an actual test/build matrix. The gap in this review isn't code quality — it's that six sprints of breadth happened without a single checkpoint that re-asks "are the P0 security items from the brief still open?" That's a process fix, not a rewrite.
