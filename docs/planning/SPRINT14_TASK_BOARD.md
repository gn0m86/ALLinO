# Sprint 14 Task Board

Opened: 2026-07-02

## Scope decision

`CLAUDE.md` §3 lists Wave 3 as Rocket.Chat, WhatsApp Business, Viber — the
only integration wave never started (confirmed by grep before starting: zero
hits for "rocket"/"viber"/"whatsapp", case-insensitive, in `backend/app`).
Prior sprint boards (Sprint 11/12/13) all carried an explicit guardrail note
telling future agents not to start Wave 3 without opening a board first —
this board is that decision, made by the agent under the user's standing
"choose the next scoped/reversible unit of work yourself" delegation.

This sprint scopes **one connector, not all three**: Rocket.Chat only. The
three Wave 3 sources don't share one shape the way Zoom+Teams did in Sprint 6
(both OAuth-bearer REST APIs) — WhatsApp Business is Meta's Graph API with
phone-number-based addressing and mandatory webhook signature verification,
Viber is a proprietary bot-API shape, and Rocket.Chat is a self-hosted REST
API closest to the existing GitLab (configurable `base_url`) + Discord
(chat-message mapping shape) connectors already in this codebase. Bundling
three different auth/data models in one unit increases risk for no benefit;
WhatsApp Business and Viber are left for their own future sprints.

## S14-01: Rocket.Chat connector (REST polling, on-demand sync)

Status: closed

- New connector: `backend/app/connectors/rocketchat_connector.py`.
  `RocketChatConnector` on the same `BaseConnector` contract as all 10
  existing connectors (start/stop/health/fetch_events,
  `RetryPolicy`/`run_with_retry` reuse — 429/5xx retry, 4xx fail-fast for
  free). Auth: Rocket.Chat's REST API requires a *pair* of headers
  (`X-Auth-Token` + `X-User-Id` from a personal access token or bot user),
  unlike the single-bearer-token connectors — modeled as two secrets,
  `ALLINO_ROCKETCHAT_TOKEN` / `ALLINO_ROCKETCHAT_USER_ID`, both resolved via
  the existing env/Vault secrets path. `base_url` is configurable (like
  GitLab) because Rocket.Chat is normally self-hosted, no fixed API host.
  Maps `GET {base_url}/api/v1/channels.messages?roomId=...` response
  `messages[]` to UnifiedEvent using the same chat-message shape as Discord
  (`channel:message_id` external id, `sender | content` preview).
- New sync endpoint: `POST /api/v1/ingestion/connectors/rocketchat/sync`
  (tenant-scoped, `require_connector_sync_permission`, optional `channel_id`
  override), reusing the shared `_run_connector_sync(...)` helper — telemetry,
  connector-registry upsert, run history, event-bus routing, and audit
  logging all come for free.
- Capability matrix (`GET /connectors/capabilities`) and frontend
  `Sidebar.tsx` source map updated with a `rocketchat` entry, following the
  exact pattern of every prior connector addition.
- Tests: `backend/tests/test_rocketchat_connector.py` (mapping, seeded fetch,
  retry success/exhaustion, 401 fail-fast, 429 retry — same shape as the
  Discord/GitLab test suites), `backend/tests/test_rocketchat_sync_endpoint.py`
  (seeded ingest, error-path persistence). `test_connector_capabilities_endpoint.py`
  extended for the new source.

- Verified: backend `pytest -q` => 213 passed (up from 202);
  `ruff check app tests --select F,E9` => all checks passed. Frontend:
  `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification (per `CLAUDE.md` §6, mandatory): seeded two
  Rocket.Chat messages via the sync endpoint against a real running backend,
  confirmed in a real browser that: the Sources panel shows `rocketchat`
  healthy with sync telemetry (p:2 i:2 r:0), the Connector Operations panel
  and Recent Runs both show the sync, the inbox filter bar gets a
  `rocketchat` chip, both messages render in the inbox list with the correct
  `channel | sender | content` preview shape, opening a message's thread
  renders correctly with the fallback source badge (not in `ThreadPanel`'s
  `SOURCE_MAP`, same as every other Wave 2/Google Calendar source — falls
  back to the generic style, not an error), and the composer honestly states
  "Replies aren't supported for rocketchat yet" (deliberately not added to
  `REPLY_SUPPORTED_SOURCES`). Settings panel's Connected Sources list shows
  `rocketchat` as "needs a secret configured" (correct — no env var set in
  this verification run). Zero unexpected console errors. Frontend rebuilt
  afterward without the sandbox-only backend URL override.

## Explicitly out of scope for this sprint

- WhatsApp Business and Viber (the other two Wave 3 sources) — different
  auth/data models, separate future sprints.
- Reply/write-back for `rocketchat` — out of scope for the same reason reply
  was scoped to Telegram/Slack only in Sprint 11; can be added later, this
  connector's `external_id` (`channel:message_id`) already carries enough to
  address a reply via `chat.postMessage`-equivalent if that's ever prioritized.
- Manual "sync now" trigger from the UI — consistent with every other
  connector in this codebase (see the Sprint 13 board for the reasoning).
