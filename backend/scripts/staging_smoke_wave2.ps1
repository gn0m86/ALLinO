param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,

    [Parameter(Mandatory = $true)]
    [string]$TenantId,

    [Parameter(Mandatory = $true)]
    [string]$ApiKey,

    [Parameter(Mandatory = $false)]
    [switch]$RequireExternalWorker,

    [Parameter(Mandatory = $false)]
    [string]$OutputPath = "./staging_smoke_wave2_result.json"
)

$ErrorActionPreference = "Stop"

function Invoke-AllinoJson {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("GET", "POST")]
        [string]$Method,

        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $false)]
        [object]$Body = $null
    )

    $uri = "$BackendUrl$Path"
    $headers = @{
        "X-API-Key"   = $ApiKey
        "X-Tenant-Id" = $TenantId
    }

    if ($Method -eq "GET") {
        return Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    }

    if ($null -eq $Body) {
        return Invoke-RestMethod -Method Post -Uri $uri -Headers $headers
    }

    $json = $Body | ConvertTo-Json -Depth 12
    return Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -ContentType "application/json" -Body $json
}

$result = [ordered]@{
    executed_at = (Get-Date).ToString("o")
    backend_url = $BackendUrl
    tenant_id   = $TenantId
    settings    = [ordered]@{ require_external_worker = [bool]$RequireExternalWorker }
    checks      = [ordered]@{}
    errors      = @()
}

try {
    $health = Invoke-AllinoJson -Method "GET" -Path "/health"
    $result.checks.health = @{ ok = $true; response = $health }
}
catch {
    $result.checks.health = @{ ok = $false }
    $result.errors += "health failed: $($_.Exception.Message)"
}

try {
    $zoomSeed = @{
        retry_max_attempts    = 3
        retry_backoff_seconds = 0.0
        seeded_events         = @(
            @{
                id         = "stg-zoom-1"
                uuid       = "stg-zoom-uuid-1"
                topic      = "Staging Zoom smoke"
                host_email = "ops@example.com"
                start_time = "2026-07-01T11:30:00Z"
            }
        )
    }
    $zoomResp = Invoke-AllinoJson -Method "POST" -Path "/api/v1/ingestion/connectors/zoom/sync?tenant_id=$TenantId" -Body $zoomSeed
    $result.checks.zoom_sync = @{ ok = $true; response = $zoomResp }
    if ($RequireExternalWorker -and $zoomResp.event_bus -ne "external_worker") {
        $result.errors += "zoom_sync event_bus expected external_worker, got $($zoomResp.event_bus)"
    }
}
catch {
    $result.checks.zoom_sync = @{ ok = $false }
    $result.errors += "zoom_sync failed: $($_.Exception.Message)"
}

try {
    $teamsSeed = @{
        retry_max_attempts    = 3
        retry_backoff_seconds = 0.0
        seeded_messages       = @(
            @{
                id              = "stg-teams-1"
                chatId          = "stg-chat-1"
                createdDateTime = "2026-07-01T13:00:00Z"
                body            = @{ content = "Staging Teams smoke" }
                from            = @{ user = @{ displayName = "Ops Bot" } }
            }
        )
    }
    $teamsResp = Invoke-AllinoJson -Method "POST" -Path "/api/v1/ingestion/connectors/teams/sync?tenant_id=$TenantId" -Body $teamsSeed
    $result.checks.teams_sync = @{ ok = $true; response = $teamsResp }
    if ($RequireExternalWorker -and $teamsResp.event_bus -ne "external_worker") {
        $result.errors += "teams_sync event_bus expected external_worker, got $($teamsResp.event_bus)"
    }
}
catch {
    $result.checks.teams_sync = @{ ok = $false }
    $result.errors += "teams_sync failed: $($_.Exception.Message)"
}

try {
    $connectors = Invoke-AllinoJson -Method "GET" -Path "/api/v1/ingestion/connectors?tenant_id=$TenantId"
    $result.checks.connectors_registry = @{ ok = $true; response = $connectors }
}
catch {
    $result.checks.connectors_registry = @{ ok = $false }
    $result.errors += "connectors registry failed: $($_.Exception.Message)"
}

try {
    $audit = Invoke-AllinoJson -Method "GET" -Path "/api/v1/ingestion/audit?tenant_id=$TenantId&limit=30"
    $result.checks.audit = @{ ok = $true; response = $audit }
}
catch {
    $result.checks.audit = @{ ok = $false }
    $result.errors += "audit failed: $($_.Exception.Message)"
}

try {
    $stats = Invoke-AllinoJson -Method "GET" -Path "/api/v1/ingestion/stats?tenant_id=$TenantId"
    $result.checks.stats = @{ ok = $true; response = $stats }
}
catch {
    $result.checks.stats = @{ ok = $false }
    $result.errors += "stats failed: $($_.Exception.Message)"
}

$result.overall_ok = ($result.errors.Count -eq 0)

$result | ConvertTo-Json -Depth 20 | Set-Content -Path $OutputPath -Encoding UTF8

if ($result.overall_ok) {
    Write-Host "Staging smoke completed successfully. Output: $OutputPath"
    exit 0
}

Write-Host "Staging smoke completed with errors. Output: $OutputPath"
exit 1
