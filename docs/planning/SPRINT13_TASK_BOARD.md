# Sprint 13 Task Board

Opened: 2026-07-02

## Scope decision

Sprint 10 (`CLAUDE.md` §5, "Extensible Connector Architecture") shipped the
Generic HTTP Connector + Webhook Receiver as an API-only MVP — `docs/planning`
and `CURRENT_STATE.md` both explicitly flagged "no frontend UI for Generic
HTTP Connector management" as a known, deliberate gap ever since. This sprint
closes that gap.

Picked over the other open items (Wave 3 integrations, Google Calendar
push/watch-channel renewal, reply/write-back for the other 8 connector
sources) because it is the only one that is pure frontend work on top of an
already-implemented, already-tested backend API — no new infrastructure, no
new integrations, no new security surface. Wave 3 remains explicitly blocked
without its own board (per the Sprint 11/12 guardrail notes); the other two
need real design decisions (scheduler infra, per-connector data model) that
don't fit a single scoped/reversible unit of work.

## S13-01: Generic HTTP Connector management UI

Status: closed

- New frontend types in `frontend/src/lib/types.ts`: `GenericConnectorConfig`,
  `GenericConnectorCreateInput`, `GenericConnectorFieldMapping`,
  `GenericConnectorAuthMethod`.
- New API client functions in `frontend/src/lib/api.ts`:
  `fetchGenericConnectors`, `createGenericConnector`,
  `deleteGenericConnector` — hitting the existing
  `GET/POST /api/v1/ingestion/connectors/generic` and
  `DELETE /api/v1/ingestion/connectors/generic/{id}` endpoints from Sprint 10.
  No manual "sync now" trigger: no other connector in this codebase exposes
  one from the frontend either (sync is externally triggered — cron/staging
  scripts — for all 10 built-in connectors too), so adding one here would be
  a new UX pattern, not a consistent one.
- New component `frontend/src/components/GenericConnectorsPanel.tsx`:
  self-fetching list + create form (name, base URL, auth method, conditional
  auth header name, poll interval, field mapping externalId/timestamp/preview,
  webhook toggle) + delete per row + webhook URL display when enabled.
  Loading/error-with-retry/empty states per the mandatory-states rule in
  `CLAUDE.md` §6. Coded against the existing CSS custom properties only (no
  hardcoded colors/radii), matching `SecurityCenter.tsx`/`SettingsPanel.tsx`.
- Wired into `SettingsPanel.tsx` below the existing "Connected Sources" card.

- Verified: backend `pytest -q` => 202 passed (unchanged, backend untouched this
  sprint — Sprint 10 already shipped and tested the API). Frontend:
  `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification (per `CLAUDE.md` §6, mandatory): backend started
  with `--host 0.0.0.0`, frontend built with
  `NEXT_PUBLIC_BACKEND_URL=http://host.docker.internal:8000` for the sandboxed
  browser tool (see the standing sandbox note in `CURRENT_STATE.md` §6),
  navigated to Settings. Confirmed: empty state renders ("No custom connectors
  registered yet."), "+ Add connector" opens the create form, the conditional
  "Auth header name" field appears only when auth method is API key, client
  -side validation correctly blocks submission with "Auth header name is
  required for API key auth." when left blank, a full submission (name, base
  URL, api_key auth + header, field mapping, webhook enabled) creates the
  connector and the list re-renders showing name/slug/auth method/base URL/
  webhook URL, and Delete removes it and restores the empty state. Zero
  unexpected console errors (only the pre-existing, unrelated favicon 404).
  Frontend rebuilt afterward without the sandbox-only backend URL override,
  per the standing rule that this is a local dev convenience, not a real
  config change.

## Explicitly out of scope for this sprint

- Editing an existing generic connector config (only create/delete) — no
  backend `PATCH`/`PUT` endpoint exists for this resource; adding one is a
  separate backend-plus-frontend unit of work.
- Manual "sync now" trigger from the UI (see above — inconsistent with every
  other connector's frontend surface in this codebase).
- Webhook secret management from the UI — webhook secrets are resolved via
  `ALLINO_GENERIC_{SLUG}_WEBHOOK_SECRET` through the env/Vault path, same
  security model as every other connector secret; nothing to edit here.
