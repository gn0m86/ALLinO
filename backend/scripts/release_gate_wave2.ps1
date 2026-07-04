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
    [switch]$RequireExternalWorkerDlq,

    [Parameter(Mandatory = $false)]
    [string]$RedisUrl = "redis://localhost:6379/0",

    [Parameter(Mandatory = $false)]
    [string]$DlqStream = "allino:ingestion:dlq",

    [Parameter(Mandatory = $false)]
    [string]$OutputDir = "./release_gate_wave2",

    [Parameter(Mandatory = $false)]
    [string]$PythonExecutable = "e:/My_prjts/ALLinO/.venv/Scripts/python.exe"
)

$ErrorActionPreference = "Continue"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$smokeScript = Join-Path $scriptRoot "staging_smoke_wave2.ps1"
$validatorScript = Join-Path $scriptRoot "validate_staging_smoke_wave2.py"
$reportValidatorScript = Join-Path $scriptRoot "validate_release_gate_wave2_report.py"
$evidenceBundleScript = Join-Path $scriptRoot "build_release_evidence_bundle.py"
$releaseHandoffScript = Join-Path $scriptRoot "generate_release_handoff_wave2.py"
$redactArtifactsScript = Join-Path $scriptRoot "redact_release_artifacts.py"
$dlqSmokeScript = Join-Path $scriptRoot "staging_smoke_external_worker_dlq.py"
$dlqPreflightScript = Join-Path $scriptRoot "preflight_external_worker_dlq.py"

if (-not (Test-Path $smokeScript)) {
    Write-Host "Smoke script not found: $smokeScript"
    exit 1
}

if (-not (Test-Path $validatorScript)) {
    Write-Host "Validator script not found: $validatorScript"
    exit 1
}

if (-not (Test-Path $reportValidatorScript)) {
    Write-Host "Report validator script not found: $reportValidatorScript"
    exit 1
}

if (-not (Test-Path $evidenceBundleScript)) {
    Write-Host "Evidence bundle script not found: $evidenceBundleScript"
    exit 1
}

if (-not (Test-Path $releaseHandoffScript)) {
    Write-Host "Release handoff script not found: $releaseHandoffScript"
    exit 1
}

if (-not (Test-Path $redactArtifactsScript)) {
    Write-Host "Redaction script not found: $redactArtifactsScript"
    exit 1
}

if ($RequireExternalWorkerDlq -and -not (Test-Path $dlqSmokeScript)) {
    Write-Host "DLQ smoke script not found: $dlqSmokeScript"
    exit 1
}

if ($RequireExternalWorkerDlq -and -not (Test-Path $dlqPreflightScript)) {
    Write-Host "DLQ preflight script not found: $dlqPreflightScript"
    exit 1
}

if (-not (Test-Path $PythonExecutable)) {
    Write-Host "Python executable not found: $PythonExecutable"
    exit 1
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$smokeJson = Join-Path $OutputDir "staging_smoke_wave2_result.json"
$validatorLog = Join-Path $OutputDir "staging_smoke_validator.log"
$reportValidatorLog = Join-Path $OutputDir "release_gate_wave2_report_validator.log"
$evidenceBundleLog = Join-Path $OutputDir "release_gate_wave2_bundle.log"
$releaseHandoffLog = Join-Path $OutputDir "release_gate_wave2_handoff.log"
$redactionLog = Join-Path $OutputDir "release_gate_wave2_redaction.log"
$dlqSmokeJson = Join-Path $OutputDir "staging_smoke_external_worker_dlq_result.json"
$dlqPreflightJson = Join-Path $OutputDir "staging_smoke_external_worker_dlq_preflight.json"
$reportJson = Join-Path $OutputDir "release_gate_wave2_report.json"
$reportMd = Join-Path $OutputDir "release_gate_wave2_report.md"
$bundleJson = Join-Path $OutputDir "release_gate_wave2_evidence_bundle.json"
$bundleMd = Join-Path $OutputDir "release_gate_wave2_evidence_bundle.md"
$handoffMd = Join-Path $OutputDir "release_gate_wave2_handoff.md"
$sanitizedDir = Join-Path $OutputDir "sanitized"
$redactionManifestJson = Join-Path $OutputDir "release_gate_wave2_redaction_manifest.json"

$startedAt = (Get-Date).ToString("o")

$dlqPreflightExitCode = 0
if ($RequireExternalWorkerDlq) {
    Write-Host "[0/3] Running strict DLQ preflight..."
    & $PythonExecutable $dlqPreflightScript --redis-url $RedisUrl --output $dlqPreflightJson
    $dlqPreflightExitCode = $LASTEXITCODE
    if ($dlqPreflightExitCode -ne 0) {
        Write-Host "Strict DLQ preflight failed. See: $dlqPreflightJson"
        exit 1
    }
}

Write-Host "[1/3] Running staging smoke script..."
& $smokeScript -BackendUrl $BackendUrl -TenantId $TenantId -ApiKey $ApiKey -OutputPath $smokeJson -RequireExternalWorker:$RequireExternalWorker
$smokeExitCode = $LASTEXITCODE

Write-Host "[2/3] Validating smoke evidence..."
$validatorArgs = @($validatorScript, "--input", $smokeJson)
if ($RequireExternalWorker) {
    $validatorArgs += "--require-external-worker"
}
$validatorOutput = & $PythonExecutable @validatorArgs 2>&1
$validatorOutput | Out-File -FilePath $validatorLog -Encoding utf8
$validatorExitCode = $LASTEXITCODE

$dlqExitCode = 0
if ($RequireExternalWorkerDlq) {
    Write-Host "[2.5/3] Running external worker DLQ smoke..."
    & $PythonExecutable $dlqSmokeScript --backend-url $BackendUrl --tenant-id $TenantId --api-key $ApiKey --redis-url $RedisUrl --dlq-stream $DlqStream --output $dlqSmokeJson
    $dlqExitCode = $LASTEXITCODE
}

$overallGo = ($smokeExitCode -eq 0 -and $validatorExitCode -eq 0 -and $dlqExitCode -eq 0 -and $dlqPreflightExitCode -eq 0)
$decision = if ($overallGo) { "GO" } else { "NO-GO" }
$finishedAt = (Get-Date).ToString("o")

$report = [ordered]@{
    started_at                  = $startedAt
    finished_at                 = $finishedAt
    backend_url                 = $BackendUrl
    tenant_id                   = $TenantId
    smoke_result_path           = (Resolve-Path $smokeJson).Path
    smoke_exit_code             = $smokeExitCode
    validator_log_path          = (Resolve-Path $validatorLog).Path
    validator_exit_code         = $validatorExitCode
    report_validator_log_path   = $null
    report_validator_exit_code  = $null
    evidence_bundle_log_path    = $null
    evidence_bundle_exit_code   = $null
    evidence_bundle_json_path   = $null
    evidence_bundle_md_path     = $null
    release_handoff_log_path    = $null
    release_handoff_exit_code   = $null
    release_handoff_md_path     = $null
    redaction_log_path          = $null
    redaction_exit_code         = $null
    redaction_manifest_path     = $null
    sanitized_output_dir        = $null
    require_external_worker     = [bool]$RequireExternalWorker
    require_external_worker_dlq = [bool]$RequireExternalWorkerDlq
    dlq_preflight_result_path   = if ($RequireExternalWorkerDlq) { (Resolve-Path $dlqPreflightJson).Path } else { $null }
    dlq_preflight_exit_code     = $dlqPreflightExitCode
    dlq_smoke_result_path       = if ($RequireExternalWorkerDlq) { (Resolve-Path $dlqSmokeJson).Path } else { $null }
    dlq_smoke_exit_code         = $dlqExitCode
    decision                    = $decision
    overall_go                  = $overallGo
}

$report | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportJson -Encoding utf8

Write-Host "[3/3] Validating release gate report..."
$reportValidatorArgs = @($reportValidatorScript, "--input", $reportJson)
if ($RequireExternalWorkerDlq) {
    $reportValidatorArgs += "--require-strict-dlq"
}
$reportValidatorOutput = & $PythonExecutable @reportValidatorArgs 2>&1
$reportValidatorOutput | Out-File -FilePath $reportValidatorLog -Encoding utf8
$reportValidatorExitCode = $LASTEXITCODE

$report.report_validator_log_path = (Resolve-Path $reportValidatorLog).Path
$report.report_validator_exit_code = $reportValidatorExitCode

$overallGo = ($overallGo -and $reportValidatorExitCode -eq 0)
$decision = if ($overallGo) { "GO" } else { "NO-GO" }
$report.overall_go = $overallGo
$report.decision = $decision

$report | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportJson -Encoding utf8

Write-Host "[3.3/3] Building release evidence bundle..."
$evidenceBundleArgs = @($evidenceBundleScript, "--report", $reportJson, "--output-manifest", $bundleJson, "--output-summary", $bundleMd)
if ($RequireExternalWorkerDlq) {
    $evidenceBundleArgs += "--require-strict-dlq"
}
$evidenceBundleOutput = & $PythonExecutable @evidenceBundleArgs 2>&1
$evidenceBundleOutput | Out-File -FilePath $evidenceBundleLog -Encoding utf8
$evidenceBundleExitCode = $LASTEXITCODE

$report.evidence_bundle_log_path = (Resolve-Path $evidenceBundleLog).Path
$report.evidence_bundle_exit_code = $evidenceBundleExitCode
$report.evidence_bundle_json_path = (Resolve-Path $bundleJson).Path
$report.evidence_bundle_md_path = (Resolve-Path $bundleMd).Path

$overallGo = ($overallGo -and $evidenceBundleExitCode -eq 0)
$decision = if ($overallGo) { "GO" } else { "NO-GO" }
$report.overall_go = $overallGo
$report.decision = $decision

$report | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportJson -Encoding utf8

Write-Host "[3.4/3] Generating release handoff markdown..."
$releaseHandoffOutput = & $PythonExecutable $releaseHandoffScript --report $reportJson --bundle $bundleJson --output $handoffMd 2>&1
$releaseHandoffOutput | Out-File -FilePath $releaseHandoffLog -Encoding utf8
$releaseHandoffExitCode = $LASTEXITCODE

$report.release_handoff_log_path = (Resolve-Path $releaseHandoffLog).Path
$report.release_handoff_exit_code = $releaseHandoffExitCode
$report.release_handoff_md_path = (Resolve-Path $handoffMd).Path

$overallGo = ($overallGo -and $releaseHandoffExitCode -eq 0)
$decision = if ($overallGo) { "GO" } else { "NO-GO" }
$report.overall_go = $overallGo
$report.decision = $decision

$report | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportJson -Encoding utf8

Write-Host "[3.6/3] Redacting release artifacts for sharing..."
$redactionOutput = & $PythonExecutable $redactArtifactsScript --report $reportJson --output-dir $sanitizedDir --output-manifest $redactionManifestJson 2>&1
$redactionOutput | Out-File -FilePath $redactionLog -Encoding utf8
$redactionExitCode = $LASTEXITCODE

$report.redaction_log_path = (Resolve-Path $redactionLog).Path
$report.redaction_exit_code = $redactionExitCode
$report.redaction_manifest_path = (Resolve-Path $redactionManifestJson).Path
$report.sanitized_output_dir = (Resolve-Path $sanitizedDir).Path

$overallGo = ($overallGo -and $redactionExitCode -eq 0)
$decision = if ($overallGo) { "GO" } else { "NO-GO" }
$report.overall_go = $overallGo
$report.decision = $decision

$report | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportJson -Encoding utf8

$mdLines = @(
    "# Wave 2 Release Gate Report",
    "",
    "- started_at: $startedAt",
    "- finished_at: $finishedAt",
    "- backend_url: $BackendUrl",
    "- tenant_id: $TenantId",
    "- smoke_result_path: $((Resolve-Path $smokeJson).Path)",
    "- smoke_exit_code: $smokeExitCode",
    "- validator_log_path: $((Resolve-Path $validatorLog).Path)",
    "- validator_exit_code: $validatorExitCode",
    "- report_validator_log_path: $((Resolve-Path $reportValidatorLog).Path)",
    "- report_validator_exit_code: $reportValidatorExitCode",
    "- evidence_bundle_log_path: $((Resolve-Path $evidenceBundleLog).Path)",
    "- evidence_bundle_exit_code: $evidenceBundleExitCode",
    "- evidence_bundle_json_path: $((Resolve-Path $bundleJson).Path)",
    "- evidence_bundle_md_path: $((Resolve-Path $bundleMd).Path)",
    "- release_handoff_log_path: $((Resolve-Path $releaseHandoffLog).Path)",
    "- release_handoff_exit_code: $releaseHandoffExitCode",
    "- release_handoff_md_path: $((Resolve-Path $handoffMd).Path)",
    "- redaction_log_path: $((Resolve-Path $redactionLog).Path)",
    "- redaction_exit_code: $redactionExitCode",
    "- redaction_manifest_path: $((Resolve-Path $redactionManifestJson).Path)",
    "- sanitized_output_dir: $((Resolve-Path $sanitizedDir).Path)",
    "- require_external_worker: $([bool]$RequireExternalWorker)",
    "- require_external_worker_dlq: $([bool]$RequireExternalWorkerDlq)",
    "- dlq_preflight_exit_code: $dlqPreflightExitCode",
    "- dlq_smoke_exit_code: $dlqExitCode",
    "- decision: $decision",
    ""
)

$mdLines | Out-File -FilePath $reportMd -Encoding utf8

Write-Host "[3.5/3] Report generated:"
Write-Host "- $reportJson"
Write-Host "- $reportMd"

if ($overallGo) {
    Write-Host "Release gate decision: GO"
    exit 0
}

Write-Host "Release gate decision: NO-GO"
exit 1
