# ALLinO Smoke Runbook (Backend Vertical Slice)

Цель: проверить путь ingestion -> persistence -> inbox -> audit.

## Preconditions

- Backend запущен на `http://localhost:8000`
- Миграции применяются автоматически на startup

## Step 1: Health

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
```

## Step 2: Seed test events

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/seed?tenant_id=tenant_demo&source=seed&count=5"
```

Ожидаем поля:

- `tenant_id`
- `processed`
- `inserted`
- `duplicates`

## Step 3: Read inbox

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/ingestion/inbox?tenant_id=tenant_demo&limit=20"
```

Ожидаем список сообщений с полями:

- `event_id`
- `tenant_id`
- `source`
- `external_id`
- `timestamp`
- `preview`

## Step 4: Verify audit trail

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/ingestion/audit?tenant_id=tenant_demo&limit=20"
```

Ожидаем записи с action:

- `ingestion.seed`
- `ingestion.seed.batch`
- `ingestion.event`

## Step 5: Manual single event ingest

```powershell
$body = @{
  eventId = "evt-manual-001"
  tenantId = "tenant_demo"
  sourceType = "manual"
  externalId = "manual-001"
  timestamp = "2026-06-25T00:00:00Z"
  payload = @{ text = "Manual event from smoke runbook" }
  schemaVersion = "1.0.0"
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/events" -ContentType "application/json" -Body $body
```

## Step 6: Validate payload without persistence (dry-run)

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/validate" -ContentType "application/json" -Body $body
```

Ожидаем поля:

- `status = valid`
- `normalized` с основными полями inbox-сообщения

## Step 7: Check aggregate stats

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/ingestion/stats?tenant_id=tenant_demo"
```

Ожидаем поля:

- `inbox_count`
- `audit_count`

## Step 8: GitHub connector sync (seeded notifications)

```powershell
$githubBody = @{
  seeded_notifications = @(
    @{
      id = "gh-smoke-001"
      updated_at = "2026-06-25T10:00:00Z"
      reason = "review_requested"
      subject = @{ title = "Review PR #100"; type = "PullRequest" }
      repository = @{ full_name = "org/repo" }
    },
    @{
      id = "gh-smoke-002"
      updated_at = "2026-06-25T10:05:00Z"
      reason = "mention"
      subject = @{ title = "Issue mention"; type = "Issue" }
      repository = @{ full_name = "org/repo" }
    }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/connectors/github/sync?tenant_id=tenant_demo" -ContentType "application/json" -Body $githubBody
```

Ожидаем поля:

- `processed`
- `inserted`
- `duplicates`
- `rejected`
- `health`

## Step 9: GitLab connector sync (seeded notifications)

```powershell
$gitlabBody = @{
  seeded_notifications = @(
    @{
      id = 201
      created_at = "2026-06-25T11:00:00Z"
      action_name = "mentioned"
      target_title = "Fix pipeline"
      target_type = "MergeRequest"
      target_url = "https://gitlab.com/org/repo/-/merge_requests/21"
      project = @{ path_with_namespace = "org/repo" }
    },
    @{
      id = 202
      created_at = "2026-06-25T11:05:00Z"
      action_name = "approved"
      target_title = "Release prep"
      target_type = "MergeRequest"
      target_url = "https://gitlab.com/org/repo/-/merge_requests/22"
      project = @{ path_with_namespace = "org/repo" }
    }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/connectors/gitlab/sync?tenant_id=tenant_demo" -ContentType "application/json" -Body $gitlabBody
```

Ожидаем поля:

- `processed`
- `inserted`
- `duplicates`
- `rejected`
- `health`

## Step 10: Linear connector sync (seeded events)

```powershell
$linearBody = @{
  seeded_events = @(
    @{
      id = "lin-201"
      identifier = "ENG-201"
      title = "Improve alerts"
      url = "https://linear.app/org/issue/ENG-201"
      createdAt = "2026-06-25T12:10:00Z"
      state = @{ name = "Backlog" }
      team = @{ key = "ENG" }
    },
    @{
      id = "lin-202"
      identifier = "ENG-202"
      title = "Refine sync"
      url = "https://linear.app/org/issue/ENG-202"
      createdAt = "2026-06-25T12:15:00Z"
      state = @{ name = "In Progress" }
      team = @{ key = "ENG" }
    }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/connectors/linear/sync?tenant_id=tenant_demo" -ContentType "application/json" -Body $linearBody
```

Ожидаем поля:

- `processed`
- `inserted`
- `duplicates`
- `rejected`
- `health`

## Done criteria

- Health = ok
- Seed returns non-zero `inserted`
- Inbox содержит seeded/manual события
- Audit содержит действия ingestion
- Validate endpoint возвращает корректный dry-run результат
- Stats endpoint возвращает положительные aggregate counts
- GitHub connector sync возвращает `inserted > 0` и добавляет события source=`github` в inbox
- GitLab connector sync возвращает `inserted > 0` и добавляет события source=`gitlab` в inbox
- Linear connector sync возвращает `inserted > 0` и добавляет события source=`linear` в inbox
- Slack connector sync возвращает `inserted > 0` и добавляет события source=`slack` в inbox
- Discord connector sync возвращает `inserted > 0` и добавляет события source=`discord` в inbox
- Zoom connector sync возвращает `inserted > 0` и добавляет события source=`zoom` в inbox
- Teams connector sync возвращает `inserted > 0` и добавляет события source=`teams` в inbox

## Step 11: Event-bus mode smoke (Redis Streams)

Preconditions:

- Redis доступен локально (например, `docker run -p 6379:6379 redis:7`)
- Backend запущен с env:
  - `ALLINO_EVENT_BUS_ENABLED=true`
  - `ALLINO_REDIS_URL=redis://localhost:6379/0`
  - `ALLINO_REDIS_STREAM_PREFIX=allino:ingestion`

Повторно запусти любой connector sync (например GitHub из шага 8), затем проверь:

1. В ответе sync есть поле `event_bus` со значением `redis_stream` или `redis_fallback`.
2. В audit для действия `connector.github.sync.batch` в metadata присутствует блок `event_bus`.

Пример проверки audit (последние записи):

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/ingestion/audit?tenant_id=tenant_demo&limit=5"
```

Ожидаемое поведение:

- при доступном Redis: `event_bus = redis_stream`
- при недоступном Redis: `event_bus = redis_fallback` и ingest не падает

## Step 11b: External event-bus worker mode smoke (separate process)

Preconditions:

- Redis доступен
- Отдельный worker запущен: `python -m app.workers.event_bus_worker`
- Worker healthcheck проходит: `python -m app.workers.event_bus_worker --healthcheck`
- Backend запущен с env:
  - `ALLINO_EVENT_BUS_ENABLED=true`
  - `ALLINO_EVENT_BUS_EXTERNAL_WORKER_ENABLED=true`
  - `ALLINO_EVENT_BUS_EXTERNAL_WORKER_TIMEOUT_SECONDS=5`
  - `ALLINO_REDIS_URL=redis://localhost:6379/0`
  - `ALLINO_REDIS_STREAM_PREFIX=allino:ingestion`

Повторно запусти любой connector sync (например GitHub из шага 8).

Ожидаемое поведение:

- в ответе sync: `event_bus = external_worker`
- при недоступном worker: `event_bus = redis_fallback` с причиной `external_worker_timeout`

Release gate для этого режима:

```powershell
./backend/scripts/release_gate_wave2.ps1 -BackendUrl http://localhost:8000 -TenantId tenant_demo -ApiKey <api-key> -RequireExternalWorker
```

## Step 11c: Strict external worker DLQ smoke (required evidence mode)

Preconditions:

- External worker mode из Step 11b включен и стабилен.
- В staging/runtime задано:
  - `ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX=connector.zoom.sync`

Зачем это нужно:

- Создать детерминированный отказ worker для smoke-вызова и проверить end-to-end путь DLQ + fallback.

Команда строгого release gate с DLQ-проверкой:

```powershell
./backend/scripts/release_gate_wave2.ps1 -BackendUrl http://localhost:8000 -TenantId tenant_demo -ApiKey <api-key> -RequireExternalWorker -RequireExternalWorkerDlq -RedisUrl redis://localhost:6379/0 -DlqStream allino:ingestion:dlq
```

Что делает gate в strict DLQ режиме:

1. `[0/3]` запускает preflight (`preflight_external_worker_dlq.py`) и проверяет env + Redis доступность.
2. `[1/3]` выполняет базовый smoke.
3. `[2/3]` валидирует smoke evidence.
4. `[2.5/3]` выполняет отдельный DLQ smoke.
5. `[3/3]` валидирует итоговый release gate report (`validate_release_gate_wave2_report.py`).
6. `[3.3/3]` собирает release evidence bundle (`build_release_evidence_bundle.py`).
7. `[3.4/3]` генерирует release handoff страницу (`generate_release_handoff_wave2.py`).
8. `[3.6/3]` генерирует sanitized copy артефактов (`redact_release_artifacts.py`).

Ожидаемый результат DLQ smoke:

1. Сформирован артефакт `staging_smoke_external_worker_dlq_result.json` в output-директории gate.
2. В артефакте `ok=true`, `dlq_delta>0`, `event_bus=redis_fallback`, `observed_reason=external_worker_error_result`.
3. В release gate report: `dlq_smoke_exit_code=0`, итоговое решение `GO`.
4. В output появляются bundle-артефакты:

- `release_gate_wave2_evidence_bundle.json`
- `release_gate_wave2_evidence_bundle.md`

5. В output появляется handoff-артефакт:

- `release_gate_wave2_handoff.md`

6. В output появляются redaction-артефакты:

- `release_gate_wave2_redaction_manifest.json`
- `sanitized/` (sanitized copies для безопасного шеринга)

Опциональная ручная пост-валидация итогового report (обычно не нужна, т.к. встроена в gate):

```powershell
e:/My_prjts/ALLinO/.venv/Scripts/python.exe backend/scripts/validate_release_gate_wave2_report.py --input ./release_gate_wave2/release_gate_wave2_report.json --require-strict-dlq
```

## Step 12: Slack connector sync (seeded messages)

```powershell
$slackBody = @{
  channel_id = "C-OPS"
  seeded_messages = @(
    @{
      ts = "1751367000.000100"
      text = "[P1] auth latency crossing threshold"
      user = "UOPS"
      channel = "C-OPS"
      type = "message"
    },
    @{
      ts = "1751367060.000200"
      text = "incident channel created"
      user = "UOPS"
      channel = "C-OPS"
      type = "message"
    }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/connectors/slack/sync?tenant_id=tenant_demo" -ContentType "application/json" -Body $slackBody
```

Ожидаем поля:

- `processed`
- `inserted`
- `duplicates`
- `rejected`
- `health`

## Step 13: Discord connector sync (seeded messages)

```powershell
$discordBody = @{
  channel_id = "987"
  seeded_messages = @(
    @{
      id = "dc-smoke-001"
      timestamp = "2026-07-01T12:10:00Z"
      content = "API latency spike in us-east"
      channel_id = "987"
      author = @{ username = "ops-bot" }
    },
    @{
      id = "dc-smoke-002"
      timestamp = "2026-07-01T12:12:00Z"
      content = "incident acknowledged"
      channel_id = "987"
      author = @{ username = "ops-bot" }
    }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/connectors/discord/sync?tenant_id=tenant_demo" -ContentType "application/json" -Body $discordBody
```

Ожидаем поля:

- `processed`
- `inserted`
- `duplicates`
- `rejected`
- `health`

## Step 14: Zoom connector sync (seeded events)

```powershell
$zoomBody = @{
  seeded_events = @(
    @{
      id = "823456"
      uuid = "uuid-1"
      topic = "Daily Incident Sync"
      host_email = "ops@example.com"
      start_time = "2026-07-01T11:30:00Z"
      join_url = "https://zoom.us/j/823456"
    },
    @{
      id = "823457"
      uuid = "uuid-2"
      topic = "Postmortem Review"
      host_email = "ops@example.com"
      start_time = "2026-07-01T12:30:00Z"
      join_url = "https://zoom.us/j/823457"
    }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/connectors/zoom/sync?tenant_id=tenant_demo" -ContentType "application/json" -Body $zoomBody
```

Ожидаем поля:

- `processed`
- `inserted`
- `duplicates`
- `rejected`
- `health`

## Step 15: Teams connector sync (seeded messages)

```powershell
$teamsBody = @{
  seeded_messages = @(
    @{
      id = "msg-100"
      chatId = "chat-1"
      createdDateTime = "2026-07-01T13:00:00Z"
      body = @{ content = "prod deploy approved" }
      from = @{ user = @{ displayName = "Ops Bot" } }
      webUrl = "https://teams.microsoft.com/l/message/msg-100"
    },
    @{
      id = "msg-101"
      chatId = "chat-1"
      createdDateTime = "2026-07-01T13:05:00Z"
      body = @{ content = "rollback plan ready" }
      from = @{ user = @{ displayName = "Ops Bot" } }
      webUrl = "https://teams.microsoft.com/l/message/msg-101"
    }
  )
} | ConvertTo-Json -Depth 8

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/ingestion/connectors/teams/sync?tenant_id=tenant_demo" -ContentType "application/json" -Body $teamsBody
```

Ожидаем поля:

- `processed`
- `inserted`
- `duplicates`
- `rejected`
- `health`
