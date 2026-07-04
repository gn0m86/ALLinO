# ALLinO Agent Start Template (60 sec)

Purpose: fast and consistent startup checklist for any new AI agent session.

## 0) Inputs

Before starting, confirm:

- workspace root is project root
- target is Sprint 1 scope unless user explicitly changes it
- no edits in docs/agent-answers/incoming/\* without explicit request

## 1) Read Order (strict, 60 sec)

1. ../../CLAUDE.md
2. ../../PROJECT_MASTER_BRIEF.md (sections 1.2, 1.3, 1.4)
3. ./CURRENT_STATE.md
4. ./SPRINT1_TASK_BOARD.md
5. ./SMOKE_RUNBOOK.md

## 2) First Action Rules

- Move exactly one relevant task to In Progress in Sprint board notes (or state which task you are taking).
- Implement only minimum change needed for Sprint exit criteria.
- Keep security-first/privacy-first/local-first/read-first constraints intact.

## 3) Mandatory Safety Checks

- Do not widen scope to write-back paths.
- Do not add Wave 2/3 integrations in Sprint 1.
- If changing persistence, verify migrations are applied on startup.
- If changing API behavior, run smoke steps for impacted endpoints.

## 4) Session Output Contract

At the end of each meaningful change batch, update:

1. ./SPRINT1_TASK_BOARD.md
2. ./CURRENT_STATE.md

And include in final handoff:

- what changed
- why changed
- test/smoke evidence
- next 1-3 actions

## 5) Quick Command Snippets

Health:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
```

Seed:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/seed?tenant_id=tenant_demo&source=seed&count=5"
```

Stats:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/ingestion/stats"
```

## 6) Anti-Drift Reminder

If a decision changes scope, security, or architecture baseline:

- add a dated note in planning docs
- reflect it in CURRENT_STATE.md
- avoid editing canonical incoming agent-answer files
