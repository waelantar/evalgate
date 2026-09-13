param(
    [string]$Image = "evalgate-api:0.9.0",
    [string]$ApiPort = "8010",
    [switch]$KeepRunning
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$artifactDir = Join-Path $repoRoot "artifacts\release"
$smokePath = Join-Path $artifactDir "eg-013d-smoke.json"

New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

function Invoke-Docker {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Arguments -join ' ') failed with exit code $LASTEXITCODE."
    }
}

function Invoke-Compose {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($Arguments -join ' ') failed with exit code $LASTEXITCODE."
    }
}

Push-Location $repoRoot
try {
    $env:EVALGATE_API_PORT = $ApiPort
    Invoke-Compose @("--profile", "release", "build", "api")

    $imageId = (& docker image inspect $Image --format "{{.Id}}").Trim()
    if ($LASTEXITCODE -ne 0 -or -not $imageId.StartsWith("sha256:")) {
        throw "Unable to inspect release-candidate image ID for $Image."
    }

    $configuredUser = (& docker image inspect $Image --format "{{.Config.User}}").Trim()
    if ($configuredUser -ne "10001:10001") {
        throw "Release-candidate image must run as UID/GID 10001:10001; found '$configuredUser'."
    }

    Invoke-Compose @("--profile", "release", "up", "-d", "db", "api")

    $liveUri = "http://127.0.0.1:$ApiPort/health/live"
    $readyUri = "http://127.0.0.1:$ApiPort/health/ready"
    $live = $null
    $ready = $null
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $live = Invoke-RestMethod -Uri $liveUri -TimeoutSec 2
            $ready = Invoke-RestMethod -Uri $readyUri -TimeoutSec 2
            if ($live.version -eq "0.9.0" -and $ready.status -eq "ready") {
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if ($null -eq $live -or $live.version -ne "0.9.0") {
        throw "Liveness smoke did not return EvalGate 0.9.0."
    }
    if ($null -eq $ready -or $ready.status -ne "ready") {
        throw "Readiness smoke did not reach ready state."
    }

    Invoke-Compose @("--profile", "release", "stop", "-t", "10", "api")

    $record = [ordered]@{
        schema_version = "1.0"
        story = "EG-013D"
        product_version = "0.9.0"
        image = $Image
        image_id = $imageId
        configured_user = $configuredUser
        liveness = $live
        readiness = $ready
        termination = @{
            command = "docker compose --profile release stop -t 10 api"
            result = "completed"
        }
        publication = "not_pushed_not_deployed"
    }
    $record | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -Path $smokePath
    Write-Host "Wrote release-candidate smoke evidence to $smokePath"
} finally {
    if (-not $KeepRunning) {
        docker compose --profile release stop api | Out-Null
    }
    Pop-Location
}
