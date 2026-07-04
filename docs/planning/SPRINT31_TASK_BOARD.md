# Sprint 31 — Multi-tenant auto-sync for built-in connectors

Opened: 2026-08-14.

## Context

At Sprint 30 close, built-in connector auto-sync (GitHub, GitLab, Jira,
Linear, Telegram, Slack, Discord, Zoom, Teams, Rocket.Chat) and Google
Calendar polling were both scoped to a single env-configured tenant
(`ALLINO_BUILTIN_CONNECTORS_POLL_TENANT_ID` / `ALLINO_GOOGLE_CALENDAR_POLL_TENANT_ID`),
because credentials for every one of those sources came from global env vars
— one GitHub token for the whole deployment, shared across every tenant.
User picked this item to build next (asked via `AskUserQuestion` among the
other known-deferred items: WhatsApp/Viber, local AI classifier).

Real fork found before writing code: how should a second/third tenant's own
credentials be stored? Existing Generic HTTP Connector precedent never
persists secrets in the DB at all (env-var-per-slug convention). Asked the
user in plain language via `AskUserQuestion`; user picked **encrypted DB
storage** over the env-var-naming-convention alternative, explicitly
accepting the tradeoff that this is the first place in the project where a
real third-party credential (not just internally-generated things like a
TOTP secret) lands in the database, even if encrypted. Reuses the existing
Fernet-based `core/crypto.py` field-level encryption (`encrypt_text`/
`decrypt_text`) already used for `messages.preview`, `connectors.last_error`,
`connector_runs.error` — no new crypto primitive, same envelope format
(`enc:v1:...`).

## 1) Storage: `builtin_connector_secrets` table

- New migration `0019_builtin_connector_secrets.sql`:
  `id, tenant_id, source_type, encrypted_config (TEXT, Fernet-encrypted JSON
  blob of {token, base_url?, user_id?, channel_id?, calendar_id?} depending
  on source), poll_interval_seconds, status, created_at, updated_at`,
  `UNIQUE(tenant_id, source_type)`. One row per (tenant, source) — covers
  all 10 built-in named connectors plus `google_calendar` (11 source types),
  unified under one table/repo instead of a separate calendar-only table,
  since the shape (tenant + source + encrypted secret blob + poll interval)
  is identical.
- New `db/repositories/builtin_connector_secrets_repo.py`: encrypts on
  write, decrypts on read (mirrors the existing per-field encrypt/decrypt
  call sites, just applied to one JSON-serialized blob instead of a single
  string column). `list_builtin_connector_secrets_with_polling()` mirrors
  `generic_connectors_repo.list_generic_connectors_with_polling()` exactly
  (status='active' AND poll_interval_seconds IS NOT NULL, across all
  tenants) for the scheduler worker to consume.

## 2) API: manage per-tenant secrets

- New `api/builtin_connector_secrets.py`, same permission tiers as
  `api/generic_connectors.py`: `require_connector_sync_permission` for
  writes, `require_ingestion_read_permission` for reads.
  - `PUT /api/v1/ingestion/connectors/builtin/{source_type}/secret` —
    upsert token + source-specific extra fields + poll_interval_seconds.
  - `GET /api/v1/ingestion/connectors/builtin/secrets` — list configured
    sources for the caller's tenant. **Never returns the decrypted secret
    values** — only `source_type`, `configured: true`,
    `poll_interval_seconds`, `status`, timestamps. Same write-only-secret
    principle as the Sprint 28 API-key-rotate endpoint.
  - `DELETE /api/v1/ingestion/connectors/builtin/{source_type}/secret`.

## 3) Scheduler: sync DB-configured tenants alongside the legacy env path

- `workers/scheduler_worker.py`: new loop over
  `list_builtin_connector_secrets_with_polling()`, keyed by the same
  `f"{tenant_id}:{source}"` due-check already used for the env-configured
  path (`_is_builtin_connector_due`) so both paths share identical
  freshness semantics. Google Calendar rows route through the existing
  `sync_google_calendar_connector`; every other source type is constructed
  directly from its connector class with `token=`/extra kwargs pulled from
  the decrypted config dict.
- **Legacy env-configured single-tenant path is kept, not replaced** —
  removing it would break existing deployments relying on
  `ALLINO_BUILTIN_CONNECTORS_POLL_*` / `ALLINO_GOOGLE_CALENDAR_POLL_*.`
  Guard added so the env path skips any `(tenant_id, source)` pair that
  already has a DB-configured row, so a tenant is never double-synced if
  both mechanisms happen to name the same tenant.

## 4) Frontend: "Your Own Credentials" panel

- New `frontend/src/components/BuiltinConnectorSecretsPanel.tsx`, same
  list-of-rows + inline-form pattern as `GenericConnectorsPanel.tsx`, but
  fixed to the 11 known source types instead of a dynamic list. Extra
  fields (`base_url`/`user_id`/`channel_id`/`calendar_id`) shown only for
  the sources that need them; Rocket.Chat's `user_id`+`base_url` enforced
  as required client-side (mirrors the API's 422). Token is a password
  input and is never redisplayed after saving (list view only shows
  `configured`/`poll_interval_seconds`/`status`, matching the API's
  write-only-secret contract).
- Mounted in `SettingsPanel.tsx` between the read-only capability list and
  `GenericConnectorsPanel`. Updated the existing capability-list helper
  text, which claimed "secrets are never entered through this UI" —
  no longer true for the deployment-wide credential note, so reworded to
  distinguish deployment-wide (env/Vault) vs. your-own (this new panel).
  Same outdated claim existed in `OnboardingScreen.tsx`'s built-in-sources
  blurb; fixed there too.
- `lib/types.ts`: `BuiltinConnectorSourceType`, `BuiltinConnectorSecretSummary`,
  `BuiltinConnectorSecretInput`. `lib/api.ts`:
  `fetchBuiltinConnectorSecrets`/`upsertBuiltinConnectorSecret`/
  `deleteBuiltinConnectorSecret`, same `baseHeaders()`/`parseErrorDetail()`
  plumbing as every other endpoint.

## Workflow change this session (not code, but load-bearing)

User asked to be able to use a persistent, always-on local instance while
development continues in parallel. Found the project had **no git
repository at all** despite 30 prior sprints — fixed by asking the user
(git init now vs. plain folder copies; Docker Compose vs. dev servers for
the persistent instance; manual "переноси"-triggered promotion vs.
automatic) and building the recommended path:
- `git init -b main`, first commit = the full working tree as of this
  sprint's backend work (274 files). `.gitignore` already correctly
  excluded `.env`/DBs/`node_modules`/`.venv` — verified before committing.
- `git worktree add ../ALLinO-dev -b dev` — this sprint's frontend half
  was built and verified in that worktree, on its own Python venv and a
  separate SQLite DB, so it never touched the user's running instance.
- Added `restart: unless-stopped` to every `docker-compose.yml` service
  (none had a restart policy before — the stack would not have survived a
  reboot). Generated a real `ALLINO_API_KEY` + `ALLINO_ENCRYPTION_KEY` into
  a git-ignored root `.env` (docker-compose already read these as
  `${VAR:-}` — just needed real values), then `docker compose up -d
  --build`. Confirmed all 5 services healthy, `/health` returns `ok`,
  auth enforced (401 without key, 200 with it).
- Promotion model going forward: user says "перенеси" (or equivalent) →
  merge `dev` into `main` in the primary worktree → `docker compose up -d
  --build` to pick up the new image. Nothing is pushed anywhere; this is
  entirely local.

## Explicitly out of scope (stated, not silent)

- WhatsApp Business / Viber — still deferred, unrelated to this sprint.
- Local AI priority classifier (Ollama) — still deferred, unrelated.
- A frontend picker that lets a tenant discover *which* built-in sources
  exist without already knowing the list — reuses the existing capability
  matrix endpoint (`/connectors/capabilities`), not a new lookup.
- Real credential *rotation* for per-tenant DB secrets — this sprint only
  adds create/update/delete (update overwrites in place); no history/audit
  trail of previous values beyond the existing generic audit log entry.

## Verified

- Backend: `pytest -q` => 396 passed (up from 324: 5 repo + 8 API + 5
  scheduler tests). `ruff check app tests --select F,E9` => all checks
  passed.
- Frontend: `tsc --noEmit` clean; `npm run build` success (Turbopack).
- **Real scheduler subprocess run** (`python -m app.workers.scheduler_worker
  --once`) against the dev DB with a real-but-invalid GitHub token stored
  via the new API: made a genuine HTTP call to `api.github.com`, got a real
  `401`, captured it gracefully in the connector registry
  (`status=error`, `last_error` populated) without crashing — confirms the
  decrypted-secret-to-connector-construction path actually works, not just
  the mocked unit tests.
- **Live browser verification, with a real finding along the way**: dev
  mode (`next dev`) silently left `mode` stuck on the Inbox view after
  clicking "Settings" — `aria-current="page"` on the button proved React
  state *did* update, but the three-pane inbox layout kept rendering
  anyway. Matches this project's known "dev-mode HMR through the sandbox's
  docker bridge produces app-shaped symptoms" quirk (see the Sprint 9
  changelog entry in `CURRENT_STATE.md`) — confirmed by switching to a
  production build (`next build && next start`), where Settings navigation,
  the onboarding screen, and the new panel all worked correctly on the
  first try. Configured a GitHub secret through the real UI (token + 300s
  poll interval) → row showed "configured · poll: 300s" with Edit/Delete;
  clicked Delete → reverted to "not configured"; zero real console errors
  (only an advisory "password field not in a form" notice). Dev servers
  reverted to normal `next dev` afterward; scratch secrets and DB rows
  cleaned up.
