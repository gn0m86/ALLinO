# ALLinO

> **Archived.** This project is no longer developed. The code is kept here as-is
> for reference; issues and pull requests are closed.

ALLinO is a **local-first, security-first unified inbox**: it pulls messages and
notifications from your work tools into one prioritized feed that runs on your own
machine. Tokens and message content stay in a local SQLite database, encrypted at
rest — nothing is sent to a third-party cloud.

## What it does

- **One feed** for chats and work tools: GitHub, GitLab, Jira, Linear, Telegram,
  Slack, Discord, Rocket.Chat, Zoom, Microsoft Teams and Google Calendar.
- **Any other source without code** via the Generic HTTP Connector (poll a REST
  endpoint with a field mapping) or an HMAC-verified webhook receiver
  (`POST /webhooks/{connector_id}`, compatible with Meta/WhatsApp and Viber signatures).
- **Prioritization and modes**: Inbox, Focus and Incident views, filters, search,
  archive, snooze, and an activity digest.
- **Reply from the inbox** for Telegram, Slack, Discord, Rocket.Chat, GitHub,
  GitLab, Jira and Linear (official APIs only).
- **Security Center** with an append-only audit log; admin actions protected by a
  TOTP second factor.

Deliberately out of scope: unofficial or scraped integrations, full "native
client" replacement, cloud storage of tokens.

## Stack

- Backend: Python, FastAPI, SQLite, optional Redis Streams event bus, background
  scheduler worker
- Frontend: Next.js (React, TypeScript)
- Security: API key and/or JWT (HS256/RS256), tenant isolation, Fernet field
  encryption, rate limiting, CSP/HSTS, optional HashiCorp Vault for secrets

## Running with Docker

1. Create a `.env` file in the repository root:

   ```env
   ALLINO_API_KEY=<random string>
   ALLINO_ENCRYPTION_KEY=<random string, 32+ characters>
   ```

   For example: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

2. Optionally add connector tokens to the same file (`ALLINO_GITHUB_TOKEN`,
   `ALLINO_TELEGRAM_BOT_TOKEN`, … — see `docker-compose.yml` for the full list), or
   enter them later in the app under **Settings → Your Own Credentials**.

3. Start everything:

   ```sh
   docker compose up -d --build
   ```

4. Open <http://localhost:3000>, go to **Settings → Backend Access** and enter the
   same `ALLINO_API_KEY`.

To enable admin actions (audit export, delete-all), generate a TOTP secret locally
with `python backend/scripts/generate_admin_totp_qr.py`, scan the QR code with an
authenticator app and set `ALLINO_ADMIN_TOTP_SECRET`.

## Development

```sh
# backend
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
.venv/bin/uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm ci
npm run dev
```

Local backend runs need either `ALLINO_API_KEY` or, for throwaway use only,
`ALLINO_ENV=development` with `ALLINO_ALLOW_INSECURE_DEV=true`. See
`backend/.env.example` for all settings.

Project history and design decisions live in `docs/planning/`
(`CURRENT_STATE.md` is the most complete record).

## License

[MIT](LICENSE)
