param(
    [string]$Image = "evalgate-api:0.12.3",
    [string]$ApiPort = "8012",
    [switch]$KeepRunning
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$artifactDir = Join-Path $repoRoot "artifacts\release"
$smokePath = Join-Path $artifactDir "eg-022-smoke.json"

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
$previousNoDefaultAttestations = $env:BUILDX_NO_DEFAULT_ATTESTATIONS
try {
    $env:EVALGATE_API_PORT = $ApiPort
    # Scan the shipped runtime filesystem, not BuildKit metadata for discarded
    # build stages. EG-022 generates a separate CycloneDX SBOM after the build.
    $env:BUILDX_NO_DEFAULT_ATTESTATIONS = "1"
    Invoke-Compose @("--profile", "release", "build", "api")

    $imageId = (& docker image inspect $Image --format "{{.Id}}").Trim()
    if ($LASTEXITCODE -ne 0 -or -not $imageId.StartsWith("sha256:")) {
        throw "Unable to inspect release-candidate image ID for $Image."
    }

    $configuredUser = (& docker image inspect $Image --format "{{.Config.User}}").Trim()
    if ($configuredUser -ne "10001:10001") {
        throw "Release-candidate image must run as UID/GID 10001:10001; found '$configuredUser'."
    }

    Invoke-Compose @("--profile", "release", "up", "-d", "--wait", "db")
    & uv run --python 3.13.15 --project apps/api --locked evalgate-db seed-empty
    if ($LASTEXITCODE -ne 0) {
        throw "Host-side release-candidate migration failed with exit code $LASTEXITCODE."
    }
    Invoke-Compose @("--profile", "release", "up", "-d", "api")

    $liveUri = "http://127.0.0.1:$ApiPort/health/live"
    $readyUri = "http://127.0.0.1:$ApiPort/health/ready"
    $live = $null
    $ready = $null
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $live = Invoke-RestMethod -Uri $liveUri -TimeoutSec 2
            $ready = Invoke-RestMethod -Uri $readyUri -TimeoutSec 2
            if ($live.version -eq "0.12.3" -and $ready.status -eq "ready") {
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if ($null -eq $live -or $live.version -ne "0.12.3") {
        throw "Liveness smoke did not return EvalGate 0.12.3."
    }
    if ($null -eq $ready -or $ready.status -ne "ready") {
        throw "Readiness smoke did not reach ready state."
    }

    Invoke-Compose @("--profile", "release", "stop", "-t", "10", "api")

    $record = [ordered]@{
        schema_version = "1.0"
        story = "EG-022"
        product_version = "0.12.3"
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
    if ($null -eq $previousNoDefaultAttestations) {
        Remove-Item Env:BUILDX_NO_DEFAULT_ATTESTATIONS -ErrorAction SilentlyContinue
    } else {
        $env:BUILDX_NO_DEFAULT_ATTESTATIONS = $previousNoDefaultAttestations
    }
    if (-not $KeepRunning) {
        docker compose --profile release stop api | Out-Null
    }
    Pop-Location
}
