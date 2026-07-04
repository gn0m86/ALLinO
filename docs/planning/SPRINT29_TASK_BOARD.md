# Sprint 29 — Frontend can now authenticate (X-API-Key)

Opened: 2026-08-14. Closed: 2026-08-14.

## Context

Long-standing inherited gap, flagged repeatedly since Sprint 26's board:
the frontend never sent `X-API-Key` (or a JWT), so a backend deployed with
real auth enforced (`ALLINO_ALLOW_INSECURE_DEV=false`) could never be used
through the web UI — only via `curl`/API clients. Asked the user in plain
language what remaining manual/incomplete items existed; this was the item
picked to fix, out of: (a) frontend auth, (b) Google Calendar multi-calendar
support (ruled out as non-trivial once researched — `google_calendar` is a
hardcoded source key across the capabilities matrix, Sidebar color map, and
manual sync endpoint path), (c) something else the user would name, (d) stop
here. User picked (a).

This app never issues its own JWTs (only verifies externally-issued ones, by
design — see `PROJECT_MASTER_BRIEF.md`), so a real login screen was never in
scope. The only sensible fix at this layer is: let the browser hold and send
the same `X-API-Key` a human would otherwise pass via `curl`.

## What was built

- `frontend/src/lib/api.ts`: added `getStoredApiKey()` / `setStoredApiKey()`
  (thin `localStorage` wrapper, SSR-safe via `typeof window === "undefined"`
  guards) and a `baseHeaders(extra?)` helper that always sends `X-Tenant-Id`
  and conditionally adds `X-API-Key` when a key is stored. Every one of the
  ~18 exported fetch functions in this file was switched from its own
  inline `headers: {...}` object to `headers: baseHeaders(...)` — a
  mechanical, file-wide change (done via `replace_all` on the two
  textually-identical header blocks, then three individual edits for the
  admin/TOTP call sites that also carry `X-TOTP-Code`).
- New `frontend/src/components/ApiKeySettings.tsx`: a "Backend Access" card
  in Settings (placed right after the Workspace card, before Connected
  Sources — it's about how the browser itself authenticates, not an
  admin-only action, so it doesn't belong grouped with the TOTP-gated admin
  cards). Password-type input, Save/Clear buttons, persisted to
  `localStorage`. Follows the Sprint 11 hydration lesson: the stored value
  is loaded via a mount-only `useEffect`, never read inside a `useState`
  initializer, so there's no SSR/client hydration mismatch.
- No backend changes at all — `X-API-Key` was already a fully-supported,
  already-CORS-whitelisted header; the backend side of this gap never
  existed, only the frontend's failure to send it.

## Explicitly out of scope / accepted tradeoffs (stated, not silent)

- Storing the key in `localStorage` (not `sessionStorage`) — chosen because
  "vход через интерфейс" implies persistence like a real login (survives
  browser restart), matching how a human would expect this to behave. Known
  tradeoff: a plaintext credential in browser storage is more exposed to
  XSS than a proper `httpOnly` session cookie would be — acceptable for
  this project's local-first, single-operator posture, but worth
  revisiting if this app is ever exposed multi-user over the open internet.
- No real login screen / no JWT issuance from this app — unchanged by
  design (see context above); this is purely "let the browser hold the
  existing shared key," not a new identity system.
- Google Calendar multi-calendar support — explicitly deferred this
  session; needs its own scoping pass (touches the capabilities matrix,
  Sidebar source-color map, and the manual sync endpoint path, all of which
  hardcode `"google_calendar"` as a single source key).

## Verified

- Frontend: `tsc --noEmit` clean; `npm run build` success.
- Backend: `pytest -q` => 309 passed (unchanged — this was a pure frontend
  change, no backend regression expected or found). `pip-audit` and
  `npm audit` (both full and `--omit=dev`) were also re-run this session as
  a housekeeping check (last run at Sprint 9) — both clean, no CVEs found,
  no remediation needed.
- **Live browser verification, this time against a backend that genuinely
  enforces auth** (`ALLINO_ENV=production`, `ALLINO_ALLOW_INSECURE_DEV=false`,
  a real `ALLINO_API_KEY` set) — a first for this project's live-verification
  sessions, which had always used insecure-dev mode before:
  1. Fresh browser, no key stored: every panel correctly showed a real `401`
     (Inbox, Sources, Connector Ops, Custom Connectors) — the existing
     error-state UI (from Sprint 2) handled it gracefully, no crash.
  2. Entered the real key in the new Backend Access panel, clicked Save —
     confirmation message shown immediately.
  3. Reloaded the page: key persisted across reload, every panel loaded
     real data (the seeded test message appeared in Inbox, capabilities
     list populated), zero console errors.
  4. Clicked Clear, clicked Refresh sources: `401`s reappeared immediately
     — confirms the header is read fresh on every request, not cached at
     app-load time.
  Verification processes cleaned up, `.env.local` reverted, scratch DB
  removed.
