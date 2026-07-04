# ALLinO Dev Quickstart

## 1. Backend setup

1. Перейти в [backend](../../backend)
2. Создать виртуальное окружение
3. Установить зависимости из [backend/requirements.txt](../../backend/requirements.txt)
4. Запустить API через uvicorn

### Windows PowerShell

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ALLINO_ALLOWED_ORIGINS="http://localhost:3000"
uvicorn app.main:app --reload --port 8000
```

## 2. Backend health check

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
```

Ожидаемый ответ:

```json
{ "status": "ok" }
```

## 3. Local CI checks (backend)

```powershell
Set-Location .\backend
pip install -r requirements-dev.txt
ruff check app tests --select F
pytest tests -q
python -m compileall app
```

## 4. Frontend setup (Next.js)

```powershell
Set-Location .\frontend
npm install
npm run dev
```

Текущие дефолты frontend:

- backend URL: `http://localhost:8000`
- tenant id: `tenant_demo`

Примечание: `.env.example` сохранен для следующей итерации конфигурации через env-переменные.

## 5. Current state of frontend

Frontend запускается как Next.js app shell и читает tenant-scoped inbox из backend API.

## 6. Source of truth for planning

- [PROJECT_MASTER_BRIEF.md](../../PROJECT_MASTER_BRIEF.md)
- [docs/planning/PREBUILD_SPEC_V1.md](PREBUILD_SPEC_V1.md)
- [docs/planning/SPRINT_PLAN_W1_W2.md](SPRINT_PLAN_W1_W2.md)

## 7. Staging readiness (Wave 2)

1. Follow staging protocol:

- [docs/planning/STAGING_READINESS_PACK_S6.md](STAGING_READINESS_PACK_S6.md)

2. Fill evidence template after run:

- [docs/planning/STAGING_SMOKE_EVIDENCE_TEMPLATE.md](STAGING_SMOKE_EVIDENCE_TEMPLATE.md)

3. Run automation script:

```powershell
Set-Location .\backend
.\scripts\staging_smoke_wave2.ps1 -BackendUrl "https://staging.example.com" -TenantId "tenant_staging" -ApiKey "<api-key>" -OutputPath ".\staging_smoke_wave2_result.json"
e:/My_prjts/ALLinO/.venv/Scripts/python.exe .\scripts\validate_staging_smoke_wave2.py --input .\staging_smoke_wave2_result.json

# One-command release gate (smoke + validate + report)
.\scripts\release_gate_wave2.ps1 -BackendUrl "https://staging.example.com" -TenantId "tenant_staging" -ApiKey "<api-key>" -OutputDir ".\release_gate_wave2"
```
