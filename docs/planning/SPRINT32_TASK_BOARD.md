# Sprint 32 Task Board

Opened: 2026-07-16. Scope: generalize the Generic HTTP Connector + Webhook
Receiver to actually support WhatsApp Business Cloud API / Viber-shaped
payloads, config-only — not a new connector architecture.

## Context / why this sprint exists

User asked to check status and continue improvements ("проверь на чем
остановились и продолжай улучшения"). Status check found:

- The only in-flight work (Google Calendar OAuth refresh-token support, `dev`
  commit `1ea0cc5`) is blocked on the user obtaining real Google Cloud Console
  credentials — nothing to build there right now.
- Every other previously-identified gap (WhatsApp/Viber, Postgres+RLS, local
  AI classifier, Telegram MTProto, JWT role management) had been explicitly
  deferred by the user in past sessions, each needing either new
  infrastructure or a standing decision not to build yet.

Asked the user directly via `AskUserQuestion` whether to wait on the Calendar
OAuth credentials or pick something else; user said to choose and proceed
("Сам выбери и делай").

**Before picking, re-verified a load-bearing assumption from prior sessions**
(via a research subagent reading the actual code, not just prior memory/docs):
project history said WhatsApp/Viber need "a genuinely new connector
architecture... a real architecture decision" because they're "webhook-push-
only APIs." That framing turned out to be half-wrong: the Webhook Receiver
(`POST /webhooks/{connector_id}`, HMAC-verified, `backend/app/api/
generic_connectors.py`) already exists and already handles push delivery —
built in Sprint 10. What actually blocks WhatsApp specifically is that its
payload shape (`entry[].changes[].value.messages[]`) is nested two array
levels deeper than the generic engine's `extract_items_from_payload()` could
reach (it only recognized a top-level array or a flat `items`/`data`/
`results` key), and `extract_path()` had no array-index support at all
("no array indices, MVP" — a comment already flagged this as provisional).
Viber's payload is a single flat event object per call, so it was *already*
usable via the existing engine — the only real gap for Viber was that
`_parse_timestamp` assumed epoch seconds, and Viber sends epoch
milliseconds.

**Decision: generalize the existing engine instead of writing a dedicated
WhatsApp/Viber connector.** This is smaller, safer, and squarely on-strategy
with CLAUDE.md §5's stated intent ("adding a new source = registering a
connector entry... not writing Python code") — the intent existed since
2026-06-30 but the engine hadn't actually grown far enough to deliver on it
for deeply-nested sources. It also generalizes to any *future* nested-JSON
webhook source, not just these two by name.

## What shipped

- `backend/app/connectors/generic_http_connector.py`:
  - `extract_path()` now supports numeric array-index segments
    (`"contacts.0.profile.name"`), not just dict-key traversal.
  - `extract_items_from_payload()` gained an optional `items_path` parameter:
    a dot-separated path where `[]`-suffixed segments iterate-and-flatten a
    list (e.g. `"entry[].changes[].value.messages[]"`). Without it, falls
    back to the exact original heuristics — fully backward compatible with
    every existing Generic HTTP Connector instance.
  - `_parse_timestamp()` now treats a numeric epoch value as milliseconds
    when it's implausibly large for seconds (`> 1e12`), and wraps
    `datetime.fromtimestamp` in a try/except (an out-of-range or malformed
    numeric timestamp from an arbitrary external payload now degrades to
    "now" instead of raising an unhandled 500).
- `backend/app/api/generic_connectors.py`:
  - `GenericConnectorFieldMapping` gained `items_path: str | None` — rides
    inside the existing `field_mapping` JSON blob column, so **no DB
    migration was needed**.
  - New `GET /webhooks/{connector_id}` handshake endpoint: echoes back
    `hub.challenge` when `hub.mode=subscribe` and `hub.verify_token` matches
    a per-connector secret (`ALLINO_GENERIC_{SLUG}_WEBHOOK_VERIFY_TOKEN`,
    env-or-Vault like every other secret in this system, never stored in the
    DB config row). This is the Meta Graph API webhook-subscription
    handshake — WhatsApp Business Cloud API (and other Graph API webhooks)
    won't start delivering events to a URL until this succeeds once. Opt-in
    per connector: without that secret configured, the GET still 404s exactly
    as it did before this endpoint existed.
- `frontend/src/lib/types.ts` + `frontend/src/components/
  GenericConnectorsPanel.tsx`: new optional "Items path" field in the
  Add/Edit Custom Connector form, so this is configurable entirely through
  Settings — no backend API calls required by hand.
- `backend/.env.example`: documents both new env keys and when each is
  needed.

## What this does NOT do

- Does not register a WhatsApp Business or Viber connector for the user —
  that needs their own Meta App / Viber bot credentials, which don't exist
  in this project. It makes doing so possible via config once they have
  those credentials.
- Does not add a dedicated `whatsapp_connector.py`/`viber_connector.py` named
  connector module. If a future need arises for WhatsApp/Viber-specific
  logic that the generic engine's dot-path + array-flatten model can't
  express (e.g. media download, read-receipt callbacks), that would still
  need bespoke code — this sprint only closes the "can it ingest a text
  message at all" gap.
- Does not touch Postgres/RLS, the local AI classifier, Telegram MTProto, or
  JWT role management — all still deferred exactly as before, untouched.

## Verification

- Backend: `pytest -q` => 422 passed (up from 396 at Sprint 31 close — 26 new:
  numeric array-index extraction, WhatsApp-shaped nested-array extraction,
  ms-epoch timestamp parsing, full webhook end-to-end tests for both a
  WhatsApp-shaped nested-array payload and a Viber-shaped single-object
  payload, and the GET verification-handshake happy/wrong-token/unconfigured
  paths). `ruff check app tests --select F,E9` (exact CI scope): clean.
- Frontend: `tsc --noEmit` clean. `npm run build` (production) succeeds.
- **Live browser verification** (dev worktree servers on 8001/3001,
  `host.docker.internal` per the sandbox's known docker-bridge routing —
  same setup as every prior sprint's live check): reproduced the known
  dev-mode-only quirk again on first try (`next dev`: clicking "Settings"
  updates `aria-current` but the Inbox 3-pane view keeps rendering) —
  confirmed as the sandbox/HMR quirk, not an app bug, by switching to a
  production build (`next build && next start`), where Settings navigated
  correctly on the first try, matching the Sprint 9/31 precedent exactly.
  In the production build: opened Settings, confirmed the new "Items path"
  field renders in the Add Connector form with the WhatsApp example as its
  placeholder, filled in a real WhatsApp-shaped config end-to-end (name,
  field mappings, items_path, webhook enabled), submitted it, confirmed the
  real backend created the connector and returned a live `webhook_url`, then
  deleted it. Dev servers and the scratch SQLite DB (`backend/data/
  allino.db`) cleaned up afterward; `frontend/next-env.d.ts`'s dev/prod-build
  toggle reverted.

## Status: closed
