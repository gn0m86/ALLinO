# Sprint 26 — Admin MFA (TOTP step-up) + first admin action: delete all tenant messages

Opened: 2026-07-03. Closed: 2026-07-03.

## Context

`CLAUDE.md` §4 has listed "MFA for admin paths" as a P0 security-gate item
since the project started. It stayed open through 25 sprints because no
admin surface ever existed to gate (`SettingsPanel.tsx` was 100% read-only
until this sprint). This time the user was asked directly, twice, in plain
language (not jargon) before any code was written — first whether an admin
panel was worth building at all ("да, делай"), then, after a full
plain-language walkthrough of the two possible depths, which one:

1. **MFA depth — lightweight TOTP step-up on existing auth (chosen)**,
   not a new user-account/login/session system. The rejected alternative
   (full accounts: passwords, self-issued sessions) would have been a
   multi-week architecture pivot for a service that has never issued its
   own tokens — it only ever verifies externally-issued ones — and
   `PROJECT_MASTER_BRIEF.md` explicitly scopes full RBAC/accounts to
   "cloud mode target architecture," not this local-first delivery.
2. **First protected action — delete all of a tenant's messages**
   (GDPR-style), the user's pick from three offered options.

Full architecture research (current auth model, `users` table history,
exact wording of the MFA requirement in all three planning docs) was done
via an Explore agent before entering plan mode; the plan itself was
written and approved (`EnterPlanMode`/`ExitPlanMode`) before any file was
touched — this sprint was too large and had too many real forks to just
improvise, unlike most sprints this session.

## Key architecture decision: MFA is not skipped for API-key callers

Every existing permission tier short-circuits for API-key callers,
treating the key as fully trusted. The new admin tier does **not** do
this — the TOTP check runs unconditionally after establishing admin
identity (by either path), because the entire point of a second factor is
that it applies regardless of which first factor got you in. This was the
one deliberate structural break from the existing 4-tier pattern; verified
by a dedicated test (`test_delete_requires_totp_even_for_trusted_api_key`).

## What was built

- `backend/requirements.txt`: `pyotp==2.10.0` (installed, MIT license).
- `backend/app/core/config.py`: `ALLINO_JWT_ADMIN_ROLES` (default `admin`
  only — narrower than the other 4 tiers) / `ALLINO_JWT_ADMIN_SCOPES`.
- `backend/app/core/security.py`: new `require_admin_mfa_permission()` —
  establishes admin identity (API key trusted, or JWT with admin
  role/scope), then unconditionally checks `X-TOTP-Code` against
  `get_secret_value("ALLINO_ADMIN_TOTP_SECRET")` via
  `pyotp.TOTP(secret).verify(code, valid_window=1)`. `503` if the secret
  isn't configured, `401` if the header is missing, `403` if the code is
  wrong.
- `backend/app/db/repositories/messages_repo.py`: `delete_all_messages()`
  — hard `DELETE FROM messages WHERE tenant_id = ?`, any state
  (active/archived/snoozed). Scoped to `messages` only, stated explicitly
  — `outbound_replies`/`connectors`/audit trail untouched.
- New `backend/app/api/admin.py`: `POST /api/v1/admin/tenant/messages/delete`
  (body: `{"confirm_tenant_id": "..."}`, must match the resolved tenant —
  `400` if not, defense in depth beyond the client-side UI check).
  Success is audit-logged (`admin.tenant_messages.deleted`,
  `{"deleted_count": n}`). `/api/v1/admin` is literally the "admin path"
  `CLAUDE.md` §4 refers to — a natural home for any future admin action.
- `backend/app/core/rate_limit.py`: `/api/v1/admin` added to
  `is_rate_limited_path()` — a TOTP brute-forcer is rate-limited exactly
  like the ingestion/webhook paths.
- `backend/.env.example`: documents the new env vars and exact TOTP
  enrollment steps (`python -c "import pyotp; print(pyotp.random_base32())"`,
  then add the secret to an authenticator app manually — no QR-code UI,
  consistent with "secrets never touch the UI").
- Frontend: `lib/api.ts` adds `deleteAllTenantMessages()`. New
  `components/DangerZone.tsx` — self-contained form (tenant-id-confirm
  text input, TOTP-code input, pending/error/success), rendered at the
  bottom of `SettingsPanel.tsx`, **not a 6th L1 nav section** (respects
  `CLAUDE.md` §6's fixed 5-section shell and the `Mode` type's closed
  5-value union). Delete button stays disabled until the typed
  confirmation exactly matches `RUNTIME_CONFIG.tenantId`.

## A real CORS bug found and fixed during mandatory live verification

Same class of bug as the Sprint 16 PATCH lesson, but for a header instead
of a method: `CORSMiddleware.allow_headers` is an explicit whitelist, and
the new `X-TOTP-Code` header wasn't in it. Invisible to `pytest`
(`TestClient` doesn't run real browser preflight) — only surfaced as a
real browser console error (`blocked by CORS policy: ... preflight
request doesn't pass access control check`) during the live-browser
verification step. Fixed by adding `"X-TOTP-Code"` to `allow_headers` in
`main.py`. Added a permanent regression test,
`test_cors_preflight_allows_totp_header_for_admin_delete` in
`test_cors_methods.py` (mirrors the existing PATCH-preflight test) —
asserts a real `OPTIONS` preflight response includes the header, not just
that the endpoint works via `TestClient`.

## A test-suite fragility found and fixed (not a regression from this feature)

Adding `test_admin_actions.py` (9 tests hitting a shared endpoint
repeatedly) pushed `backend/app/core/rate_limit.py`'s module-level
`RATE_LIMITER` singleton — a real wall-clock sliding window, never reset
between test files — over threshold for unrelated later test files
(`test_message_actions.py`, `test_metrics.py`), causing order-dependent
flakiness that had nothing to do with those tests' own behavior. Root
cause, not new: the limiter was already a shared, never-reset singleton;
this sprint's tests just happened to add enough request volume to trip it
for the first time. Fixed at the root: `tests/conftest.py`'s
`pytest_runtest_setup` (which already resets other global security state
before every test) now also calls `rate_limit.RATE_LIMITER.clear()` —
fixes this specific flakiness and prevents any future test file from
causing it again, not just a workaround scoped to this one file.

## Verified

- Backend: `pytest -q` => 298 passed (up from 288: 9 new
  `test_admin_actions.py` tests + 1 new CORS regression test). `ruff check
  app tests --select F,E9` clean. Test coverage: 503 without TOTP secret
  configured, 401 without the header, 403 on a wrong code (message
  survives), 400 on a `confirm_tenant_id` mismatch (message survives),
  full success path (deletes active + archived + snoozed messages,
  accurate count, audited), tenant isolation, JWT-admin-role path works,
  JWT-without-admin-role is `403` even with a valid TOTP code, and the key
  structural test (API key alone is *not* sufficient — TOTP still
  required).
- Frontend: `tsc --noEmit` clean; `npm run build` success.
- **Live browser verification** (real backend + real frontend, sandboxed
  browser tool, zero permission prompts): generated a real TOTP secret via
  `pyotp.random_base32()`, configured it on a scratch backend, seeded 5
  messages. Opened Settings → Danger Zone: delete button correctly stayed
  disabled until the tenant id was typed exactly. Submitted with a
  deliberately wrong code first — hit the CORS bug above (fixed live,
  backend restarted, re-verified with the same 5 still-seeded messages
  intact). After the fix: wrong-code attempt correctly showed "Invalid
  TOTP code" inline and left all 5 messages untouched (confirmed directly
  against the backend). Generated a real code via
  `pyotp.TOTP(secret).now()` and submitted — "Deleted 5 messages." shown,
  cross-checked directly against the backend: `/inbox` => 0,
  `/inbox?archived=true` => 0, audit log contains
  `admin.tenant_messages.deleted` with `{"deleted_count": 5}`. Zero
  unexpected console errors after the CORS fix. Verification processes
  cleaned up, `.env.local` reverted, scratch DB removed.

## Explicitly out of scope (stated, not silent)

- Any other admin action (export audit log, rotate API key, manage JWT
  role config) — the MFA plumbing is generic; adding a second action is
  now a small, same-pattern extension, not a new architecture decision.
- Deleting `outbound_replies`/`connectors`/audit trail for the tenant
  (only `messages` rows are touched by this first action).
- TOTP enrollment UI / QR-code generation (env-only secret, same as every
  other secret in this project).
- Fixing the pre-existing "frontend never sends X-API-Key" gap — inherited
  as-is, not introduced or worsened by this feature.
