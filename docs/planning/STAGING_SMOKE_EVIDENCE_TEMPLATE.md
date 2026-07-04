# Staging Smoke Evidence Template (Wave 2)

Дата прогона: YYYY-MM-DD
Исполнитель: <name>
Среда: staging
Backend URL: https://...
Tenant: tenant_staging

## 1. Security Baseline

- ALLINO_ENV=staging: yes/no
- ALLINO_API_KEY configured: yes/no
- ALLINO_ALLOW_INSECURE_DEV=false: yes/no

## 2. Connector Secrets Present

- ALLINO_ZOOM_TOKEN: yes/no
- ALLINO_TEAMS_TOKEN: yes/no
- ALLINO_DISCORD_BOT_TOKEN (optional): yes/no
- ALLINO_DISCORD_CHANNEL_ID (optional): yes/no

## 3. Smoke Results

- Health endpoint: pass/fail
- Stats endpoint: pass/fail
- Zoom sync: pass/fail
- Teams sync: pass/fail
- Connectors registry contains zoom/teams: pass/fail
- Audit contains connector.zoom.sync actions: pass/fail
- Audit contains connector.teams.sync actions: pass/fail

## 4. Evidence Files

- JSON output from script: <path>
- Release gate report JSON: <path>
- Release gate report Markdown: <path>
- Release evidence bundle JSON: <path>
- Release evidence bundle Markdown: <path>
- Release handoff Markdown: <path>
- Redaction manifest JSON: <path>
- Sanitized artifacts directory: <path>
- Additional logs/screenshots: <paths>

## 5. Findings

- Issue 1:
- Issue 2:
- Issue 3:

## 6. Decision

- Recommendation: GO / NO-GO
- Rationale:
