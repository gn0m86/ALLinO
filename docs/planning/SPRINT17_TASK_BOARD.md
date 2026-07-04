# Sprint 17 Task Board

Opened: 2026-07-02

## Scope decision

User explicitly asked to extend reply/write-back to GitHub, GitLab, Jira,
Linear (via `AskUserQuestion`, plain-language explanation first). For these
sources "reply" means posting a comment on the underlying issue/PR/ticket,
not a chat message — a different action than the existing Telegram/Slack/
Discord/Rocket.Chat reply path, confirmed with the user before starting.

**Technical finding surfaced to the user before implementation:** Jira and
Linear are self-sufficient — their `external_id` (Jira's internal issue id,
Linear's issue id) is already exactly what each provider's comment API
needs, no extra data required. GitHub and GitLab are not: their
`external_id` is the *notification* id, not the issue/PR itself — the
actual issue/PR address only exists in the ingestion-time `payload`
(`subject_url` for GitHub, `target_url` for GitLab), which the `messages`
table has never persisted (by design — only `preview`/`thread_key`/
`priority` survive normalization, see Sprint 11). User chose: add a new
column rather than skip GitHub/GitLab.

## S17-01: `messages.reply_target` column (schema, additive)

Status: closed

- New migration `backend/migrations/0012_reply_target.sql`:
  `ALTER TABLE messages ADD COLUMN reply_target TEXT`. Nullable, unused by
  every existing source (chat sources already have everything in
  `external_id`; Jira/Linear won't need it either — see below).
- `backend/app/domain/events.py`: `InboxMessage` gets
  `reply_target: str | None = None`.
- `backend/app/services/normalizer.py`: `normalize_event(...)` populates it
  from `payload["subject_url"]` (GitHub) or `payload["target_url"]`
  (GitLab) when present; `None` for every other source. Same trust level as
  `preview` (both come from provider-supplied text — repo/project names
  already appear in `preview` too, no new information disclosed).
- `backend/app/db/repositories/messages_repo.py`: `reply_target` is
  encrypted at rest via the existing `encrypt_text`/`decrypt_text` helpers,
  same treatment as `preview` (consistent field-level encryption policy,
  `CLAUDE.md` §4).

## S17-02: Reply senders for GitHub, GitLab, Jira, Linear

Status: closed

- `backend/app/connectors/github_connector.py` adds `send_github_reply()`:
  `POST {reply_target}/comments` (subject API URL + `/comments`), `Bearer`
  token, `{"body": text}`.
- `backend/app/connectors/gitlab_connector.py` adds `send_gitlab_reply()`:
  parses the web URL in `reply_target` (`.../-/issues/{iid}` or
  `.../-/merge_requests/{iid}`, optionally with a `#note_xxx` fragment from
  the todo target) into `project_path` + `noteable_type` + `iid`, then
  `POST {base_url}/api/v4/projects/{url-encoded project_path}/{issues|merge_requests}/{iid}/notes`.
- `backend/app/connectors/jira_connector.py` adds `send_jira_reply()`:
  `POST {base_url}/rest/api/3/issue/{external_id}/comment` with Atlassian
  Document Format body (`{"body": {"type": "doc", "version": 1, "content": [...]}}`).
  Uses `external_id` directly — no `reply_target` needed.
- `backend/app/connectors/linear_connector.py` adds `send_linear_reply()`:
  GraphQL `commentCreate(input: {issueId, body})` mutation against
  `https://api.linear.app/graphql`. Uses `external_id` directly.
- `backend/app/api/replies.py`: all 4 wired into `_REPLY_TOKEN_ENV_KEYS`/
  `_REPLY_SENDERS`. New check: for `github`/`gitlab`, if the message's
  `reply_target` is empty (older message ingested before this schema
  change, or a notification whose subject wasn't a commentable issue/PR),
  reply is rejected with `400` — same "unsupported for this specific
  message" semantics as the existing unsupported-source check, not a
  `503` config problem.

## Tests

- `backend/tests/test_reply_delivery.py` extended with all 4 new senders
  (request shape, missing-target `ValueError`, API-error `RuntimeError`) —
  same shape as the existing Telegram/Slack/Discord/Rocket.Chat tests.
- `backend/tests/test_reply_endpoint.py` extended: GitHub/GitLab success
  path (seeded with a `subject_url`/`target_url`), GitHub/GitLab
  missing-`reply_target` → `400`, Jira/Linear success path (no
  `reply_target` needed).

## Verification

- Backend `pytest -q` => 252 passed (up from 233); `ruff check app tests --select F,E9` => all checks passed.
- Frontend `tsc --noEmit` clean; `npm run build` => success.
- Live browser verification (per `CLAUDE.md` §6, mandatory): seeded one
  GitHub notification, one GitLab notification, one Jira issue, and one
  Linear issue via their sync endpoints against a real running backend.
  Confirmed in a real browser that the reply composer now renders for all
  four sources (previously "not supported"), and that sending a reply on
  each — with no provider tokens configured — correctly surfaces the
  fail-closed 503 "Reply is not configured for source '...'" for all four.
  This exercises the full new code path end to end: `reply_target`
  populated at ingest time from `subject_url`/`target_url`, round-tripped
  through the encrypted `messages.reply_target` column, read back by
  `get_message()`, and reaching the token-config check in `replies.py`
  before delivery would be attempted. Zero unexpected console errors — only
  the four expected 503s. Frontend rebuilt afterward without the
  sandbox-only backend URL override.

## Explicitly out of scope for this sprint

- Reply for Zoom/Teams/Google Calendar — meeting-shaped, no reply semantics
  (unchanged from earlier sprints' reasoning).
- WhatsApp Business, Viber — unchanged, still needs an architecture
  decision (see Sprint 15/16 boards).
- Backfilling `reply_target` for GitHub/GitLab messages already ingested
  before this migration — those rows simply can't be replied to until
  re-ingested; not treated as a bug, existing data has no way to recover
  the discarded payload.
