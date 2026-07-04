# Sprint 28 — Third admin action: rotate API key (candidate generator, not live cutover)

Opened: 2026-07-03. Closed: 2026-07-03.

## Context

Sprint 27's board explicitly deferred "rotate API key," reasoning that unlike
export-audit-log, it's "a real config-mutation decision, not a drop-in
extension" — it needed its own scoping conversation. This session the user
asked directly what "rotate API key" and "manage JWT role config" even mean
(plain-language explanation given, no jargon), then said to go ahead with
API-key rotation specifically.

## Research finding that shaped the scope

`ALLINO_API_KEY` is read from env-or-Vault **once, at process import time**
(`backend/app/core/config.py`: `ALLINO_API_KEY: str | None =
get_secret_value("ALLINO_API_KEY")`, a module-level constant, not a
per-request lookup like the admin TOTP secret is). This means a genuinely
*live* rotation (old key stops working immediately, new key works
immediately, no restart) is only possible if the key lives in Vault — the
only source the running process could re-read without restarting — and even
then, `backend/app/core/secrets.py` currently only supports *reading* from
Vault, not writing to it. Vault is also not actually running in this
project's own `docker-compose.yml` (`ALLINO_VAULT_ENABLED` defaults to
`false`, no Vault service defined) — everyone's local setup today uses the
plain `.env` path.

This was surfaced to the user directly (`AskUserQuestion`, plain language,
no jargon) as two real options:

1. **Live rotation via Vault** — needs standing up a Vault server (new
   infrastructure) plus a new Vault-write path in `secrets.py`. A bigger,
   separate piece of work.
2. **Candidate-key generator (chosen)** — an admin button generates a new
   cryptographically strong random key and shows it once; the admin
   manually puts it in `.env`/Vault and restarts the backend, same as
   today's manual process, just without having to hand-generate a random
   string. No live cutover, no new infrastructure.

User picked option 2 explicitly (marked "recommended" and picked as such).

## What was built

- `backend/app/api/admin.py`: `POST /api/v1/admin/api-key/rotate`, gated by
  the same `require_admin_mfa_permission` dependency as the other two admin
  actions (TOTP required unconditionally). Generates
  `secrets.token_urlsafe(32)` and returns it directly in the response body —
  never written to the DB, never included in the audit-log metadata (the
  audit entry, `admin.api_key.rotate_candidate_generated`, has empty
  metadata `{}` by design — the whole point is the key never touches
  persistent storage anywhere other than wherever the admin pastes it).
  Response also includes an `instructions` string spelling out the manual
  activation step, so the "not live" limitation is visible at the point of
  use, not just in docs.
- Frontend: `lib/api.ts` adds `rotateApiKeyCandidate(totpCode)`. New
  `components/ApiKeyRotatePanel.tsx` — same TOTP-gated form pattern as the
  other two admin panels, shows the generated key once in a
  read-only/select-on-focus input plus the instructions text. Mounted in
  `SettingsPanel.tsx` between `AdminAuditExport` and `DangerZone`.
  Renamed `AdminAuditExport`'s card header from generic "Admin Tools" to
  "Export Audit Log" now that there are three distinct admin action cards,
  each self-labeled (matches the existing one-component-per-action
  pattern from Sprints 26-27).

## Explicitly out of scope (stated, not silent)

- Actually activating the rotated key, or a grace/dual-key window — no live
  cutover exists at all in this design; see the research finding above for
  why (env-var caching + no Vault-write path + Vault not actually deployed
  in this project).
- Standing up Vault as real infrastructure — a separate, larger piece of
  work, not something to start opportunistically inside this sprint.
- "Manage JWT role config" — still deferred; a distinct question (this
  service has no user/role database at all, only env-configured role-name
  lists) not addressed by this sprint.

## Verified

- Backend: `pytest -q` => 309 passed (up from 304: 5 new tests — 503/no-
  secret, 401/no-header, 403/wrong-code, success path returns a >=32-char
  key and is audited with the key never appearing in the metadata, TOTP
  required even for a trusted API key). `ruff check app tests --select
  F,E9` => all checks passed.
- Frontend: `tsc --noEmit` clean; `npm run build` success.
- **Live browser verification**: wrong TOTP code showed "Invalid TOTP code"
  inline, console showed only the expected `403` (no CORS error — method/
  header were already whitelisted). Real TOTP code generated a real key,
  displayed once with the activation instructions; cross-checked directly
  against the backend: `admin.api_key.rotate_candidate_generated` audit
  entry present with `metadata: {}` (key confirmed absent from the log).
  Verification processes cleaned up, `.env.local` reverted, scratch DB
  removed.
