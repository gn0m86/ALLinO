# ALLinO Staging Readiness Pack (S6)

Дата: 2026-07-01
Цель: закрыть оставшиеся pre-production пункты после Sprint 6.

## 1. Scope

Этот пакет покрывает:

1. Проверку live staging пути для Wave 2 connectors (Zoom/Teams).
2. Фиксацию evidence по результатам smoke-run.
3. Минимальную матрицу secrets/scopes для staging.

## 2. Prerequisites

1. Staging backend доступен по HTTPS URL.
2. В staging выставлены security env значения:

- ALLINO_ENV=staging
- ALLINO_API_KEY задан
- ALLINO_ALLOW_INSECURE_DEV=false

3. Для Wave 2 заданы staging токены:

- ALLINO_ZOOM_TOKEN
- ALLINO_TEAMS_TOKEN

4. Есть тестовый tenant (например: tenant_staging).

## 3. Secrets and Scopes Matrix (staging)

| Connector          | Secret Env                                           | Minimal Scope Baseline | Rotation Policy | Status   |
| ------------------ | ---------------------------------------------------- | ---------------------- | --------------- | -------- |
| Zoom               | ALLINO_ZOOM_TOKEN                                    | meetings:read          | 90 days         | TODO     |
| Teams              | ALLINO_TEAMS_TOKEN                                   | Chat.Read              | 90 days         | TODO     |
| Discord (optional) | ALLINO_DISCORD_BOT_TOKEN + ALLINO_DISCORD_CHANNEL_ID | channel read           | 90 days         | OPTIONAL |

Примечание: конкретные provider scope names уточняются в IAM/tenant настройках организации и должны быть зафиксированы в operational wiki.

## 4. Execution Flow

1. Выполнить базовый smoke по [docs/planning/SMOKE_RUNBOOK.md](SMOKE_RUNBOOK.md).
2. Выполнить автоматический сбор evidence скриптом:

- [backend/scripts/staging_smoke_wave2.ps1](../../backend/scripts/staging_smoke_wave2.ps1)

3. Сохранить результат в json-файл и приложить к релизному тикету.
4. Провалидировать json evidence валидатором:

- `e:/My_prjts/ALLinO/.venv/Scripts/python.exe backend/scripts/validate_staging_smoke_wave2.py --input <path-to-json>`

  4.1. Провалидировать итоговый release gate report:

- обычный режим:
  - `e:/My_prjts/ALLinO/.venv/Scripts/python.exe backend/scripts/validate_release_gate_wave2_report.py --input <path-to-release_gate_wave2_report.json>`
- strict DLQ режим:
  - `e:/My_prjts/ALLinO/.venv/Scripts/python.exe backend/scripts/validate_release_gate_wave2_report.py --input <path-to-release_gate_wave2_report.json> --require-strict-dlq`

Примечание: при запуске `release_gate_wave2.ps1` report validation выполняется автоматически; команды выше нужны только для ручной перепроверки артефактов.

5. Заполнить шаблон evidence:

- [docs/planning/STAGING_SMOKE_EVIDENCE_TEMPLATE.md](STAGING_SMOKE_EVIDENCE_TEMPLATE.md)

Alternative one-command gate:

- `backend/scripts/release_gate_wave2.ps1` запускает smoke + validator + генерирует итоговый GO/NO-GO report.
- `release_gate_wave2.ps1` также собирает release evidence bundle (`release_gate_wave2_evidence_bundle.json/.md`).
- `release_gate_wave2.ps1` также генерирует release handoff markdown (`release_gate_wave2_handoff.md`).
- `release_gate_wave2.ps1` также формирует redaction manifest и sanitized копии артефактов.
- Для строгого режима DLQ evidence (external worker):
  - выставить `ALLINO_EVENT_BUS_EXTERNAL_WORKER_FORCE_ERROR_ACTION_PREFIX=connector.zoom.sync`
  - запускать gate с `-RequireExternalWorker -RequireExternalWorkerDlq`
  - gate автоматически запускает preflight env/redis проверки и пишет отдельный preflight artifact

## 5. Acceptance Criteria

1. Все ключевые endpoint проверки из скрипта завершились статусом ok.
2. Zoom sync и Teams sync вернули health и ненулевые processed/inserted на seeded payload.
3. В audit видны действия connector.zoom.sync и connector.teams.sync.
4. В connectors registry по tenant есть source_type=zoom и source_type=teams со статусом healthy или degraded (если provider-side warning).
5. Вся evidence приложена к release record.
6. Validator возвращает `GO` для приложенного json.
7. Release gate report (`decision=GO`) приложен к release record.
8. Для strict external-worker режима присутствует DLQ smoke artifact, где `ok=true` и `dlq_delta>0`.
9. Для strict external-worker режима preflight artifact содержит `ok=true` (env + redis).
10. Сформирован evidence bundle (`json` + `md`) и приложен к release record.
11. Сформирован handoff markdown и приложен к release record.
12. Сформирован redaction manifest и приложены sanitized копии артефактов для шеринга.

## 6. Go / No-Go Decision Rule

Go:

- acceptance criteria 1-5 выполнены;
- нет открытых security blockers по secrets/scopes.

No-Go:

- отсутствует стабильный доступ к provider API;
- отсутствует корректная auth конфигурация (API key/JWT) в staging;
- smoke evidence не собрана или противоречива.
