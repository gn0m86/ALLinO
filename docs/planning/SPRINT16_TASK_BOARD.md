# Sprint 16 Task Board

Opened: 2026-07-02

## Scope decision

Continuing under the user's standing "continue where you can, on your own"
delegation. Remaining known gaps: WhatsApp Business/Viber (needs an
architecture decision — see Sprint 15 board — deliberately still not
started), Google Calendar push/renewal (needs scheduler infra, deliberately
still not started), reply for issue/PR-comment/meeting-shaped sources
(different data model each, needs per-source design), and editing an
existing Generic HTTP Connector config from the UI (no backend `PATCH`
endpoint exists — flagged explicitly as a follow-up in the Sprint 13 and
Sprint 15 boards). Picked the last one: it's pure CRUD completion on a
feature that already exists end-to-end (Sprint 10 backend, Sprint 13 UI),
no new infra, no new integration, no ambiguous auth model — the safest
possible "continue without me" unit.

## S16-01: Generic HTTP Connector edit (PATCH)

Status: closed

- Backend: new `PATCH /api/v1/ingestion/connectors/generic/{config_id}` in
  `backend/app/api/generic_connectors.py`. Deliberately **immutable**:
  `name`/`slug`. Rationale: `slug` derives `source_type` (`generic:{slug}`)
  which is already referenced by historical `connector_runs`/`connectors`
  telemetry rows and the webhook secret env-var name
  (`ALLINO_GENERIC_{SLUG}_WEBHOOK_SECRET`) — changing it after creation
  would orphan history and silently break a configured webhook secret.
  Editable: `base_url`, `auth_method`, `auth_header_name`,
  `poll_interval_seconds`, `field_mapping`, `webhook_enabled`. Uses
  `exclude_unset=True` so PATCH is a true partial update (omitted fields
  untouched, not reset to null) — same `auth_header_name`-required-for-
  `api_key` validation as create, checked against the *resulting* merged
  state (an update that only changes `auth_method` to `api_key` without
  supplying a header, or that clears an existing header while
  `auth_method` stays `api_key`, is still rejected).
- New repo function `update_generic_connector(...)` in
  `backend/app/db/repositories/generic_connectors_repo.py` — dynamic
  `SET` clause built from a fixed field whitelist (not raw user keys, no
  injection surface), `updated_at = CURRENT_TIMESTAMP` set explicitly
  (SQLite's column `DEFAULT CURRENT_TIMESTAMP` only fires on INSERT, same
  pattern already used in `connectors_repo.py`'s update path).
- Frontend: `frontend/src/lib/api.ts` adds `updateGenericConnector(...)`.
  `frontend/src/components/GenericConnectorsPanel.tsx` adds an "Edit"
  button per row that opens the existing create-form UI pre-filled and
  submits a PATCH instead of a POST; name is shown read-only during edit
  (not editable, per the immutability decision above).
- Tests: `backend/tests/test_generic_connectors_repo.py` (new — repo-level
  partial update, unknown-field ignored, nonexistent-id returns `None`),
  extending `backend/tests/test_generic_connector_endpoints.py` (or the
  existing generic-connector test file, whichever exists) with PATCH
  endpoint coverage: 404 unknown id, 422 api_key-without-header on update,
  200 partial update leaves other fields untouched, tenant isolation.

- **Found and fixed a real pre-existing CORS bug while doing the mandatory
  live-browser verification (not originally in scope, same "verify live, not
  just build" pattern as the Sprint 7 CSP catch and Sprint 11 hydration
  catch):** `backend/app/main.py`'s `CORSMiddleware` had
  `allow_methods=["GET", "POST", "DELETE"]` — `PATCH` was never added when
  this list was tightened in an earlier security-hardening session, because
  no endpoint used it yet. The browser's CORS preflight (`OPTIONS`) for the
  new PATCH request failed with "It does not have HTTP ok status," and the
  actual PATCH never reached the backend at all — invisible to
  `pytest`/`tsc`/`npm build`, only visible as a real browser console error.
  Fixed: added `"PATCH"` to `allow_methods`. Added a regression test,
  `backend/tests/test_cors_methods.py`, asserting an `OPTIONS` preflight for
  the generic-connector PATCH route gets `PATCH` back in
  `Access-Control-Allow-Methods` — this class of bug won't reproduce
  silently again for future write methods either, since the test pattern is
  now established.
- Verified: backend `pytest -q` => 233 passed (up from 222);
  `ruff check app tests --select F,E9` => all checks passed. Frontend:
  `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification (per `CLAUDE.md` §6, mandatory — and this is the
  session that justified why it's mandatory): created a test connector,
  clicked "Edit," confirmed the form pre-fills correctly with `Name` shown
  disabled, changed the base URL and saved — first attempt failed with the
  CORS bug above (browser console showed the real failure `tsc`/`pytest`
  never would have caught), fixed it, retried: save succeeded, list updated
  to the new value with zero console errors. Also verified switching auth
  method to `api_key` without a header blocks save with the same
  client-side validation message as create, and that "Cancel" discards the
  unsaved edit rather than persisting it. Cleaned up the test connector via
  Delete. Frontend rebuilt afterward without the sandbox-only backend URL
  override.

## Explicitly out of scope for this sprint

- Renaming a connector / changing its slug — see immutability rationale
  above; would need a migration path for historical telemetry + webhook
  secret env vars, a separate decision if ever needed.
- WhatsApp Business, Viber, Google Calendar push/renewal, reply for
  issue/PR-comment-shaped sources — unchanged from the Sprint 15 board.
