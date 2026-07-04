# Sprint 27 — Second admin action: export tenant audit log

Opened: 2026-07-03. Closed: 2026-07-03.

## Context

Sprint 26 built the generic admin-MFA plumbing (`require_admin_mfa_permission`,
`/api/v1/admin`) and its first action (delete all tenant messages), and
explicitly named "export audit log" as a candidate second action requiring
no new architecture — just reuse of the same permission dependency. This
session opened under the user's usual open-ended "продолжай" delegation;
per the established pattern (see memory), the most scoped/reversible item
from the known-gaps list was picked without needing to ask: unlike
"rotate API key" (touches a live secret, higher blast radius) or "manage
JWT role config" (no config-write path exists yet), exporting the audit
log is read-only and trivially reversible (nothing is mutated except the
audit trail gaining one more entry for the export itself).

## What was built

- `backend/app/api/admin.py`: `GET /api/v1/admin/tenant/audit/export`,
  gated by the same `require_admin_mfa_permission` dependency as the
  delete action (X-TOTP-Code required unconditionally, even for a trusted
  API key — same structural rule as Sprint 26). Reuses the existing
  `list_audit(tenant_id, limit)` repository function directly (already
  tenant-scoped and already transparently decrypts `metadata`) with a
  fixed `limit=10000` cap — no new repository function needed, following
  the Sprint 17 lesson ("check whether the existing path is already
  sufficient before adding new plumbing"). The export itself is
  audit-logged (`admin.tenant_audit.exported`, `{"exported_count": n}`),
  same self-auditing pattern as the delete action.
- Frontend: `lib/api.ts` adds `exportTenantAudit(totpCode)` — fetches the
  export and triggers a client-side file download (Blob + object URL),
  no backend `Content-Disposition` needed. New
  `components/AdminAuditExport.tsx` — a plain (non-"danger"-styled) admin
  tools box since this action is non-destructive, just a TOTP code input
  and an "Export audit log" button. Mounted in `SettingsPanel.tsx` above
  `DangerZone` (destructive and non-destructive admin actions visually
  separated, not lumped into the danger-styled box). Still not a 6th L1
  nav section — respects `CLAUDE.md` §6's fixed 5-section shell.

## Explicitly out of scope (stated, not silent)

- Rotate API key / manage JWT role config — real config-mutation actions,
  each is its own decision (what does "rotate" mean when the key lives in
  env/Vault, not the DB?) not a drop-in extension like this one.
- A `Content-Disposition: attachment` response header from the backend —
  the frontend triggers the download client-side instead; revisit only if
  a non-browser (e.g. `curl`) consumer of this endpoint needs a real
  attachment header.
- Export limit above 10000 rows, or a streaming/paginated export — same
  reasoning as the Sprint 25 search scan-limit: documented cap, not
  hidden; revisit only if a real tenant's audit volume exceeds it.

## Verified

- Backend: `pytest -q` => 304 passed (up from 298: 6 new tests in
  `test_admin_actions.py` covering 503/no-secret, 401/no-header, 403/wrong-
  code, success + audit assertion, tenant isolation, and TOTP-required-even-
  for-trusted-API-key). `ruff check app tests --select F,E9` => all checks
  passed.
- Frontend: `tsc --noEmit` clean; `npm run build` success.
- **Live browser verification** (real backend + real frontend, sandboxed
  browser tool, zero permission prompts): seeded one message, opened
  Settings — the new "Admin Tools" box renders above Danger Zone with the
  Export button correctly disabled until a TOTP code is typed. Submitted a
  deliberately wrong code — "Invalid TOTP code" shown inline, console
  showed the expected `403` fetch failure only (no CORS preflight error,
  since `GET` and `X-TOTP-Code` were already whitelisted by Sprint 16/26 —
  nothing new needed here). Generated a real TOTP code and submitted —
  browser triggered a real file download (`tenant_demo-audit-export.json`),
  UI showed "Exported 1 audit entry.", cross-checked directly against the
  backend: `GET /api/v1/ingestion/audit` shows the new
  `admin.tenant_audit.exported` entry with `{"exported_count": 1}` matching
  what the UI reported. Zero unexpected console errors (only pre-existing
  sandbox noise: unreachable Google Fonts DNS, missing favicon — both
  present before this change too). Verification processes cleaned up,
  `.env.local` reverted to `localhost`, scratch DB removed.
