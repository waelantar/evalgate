param(
    [string]$Image = "evalgate-api:0.12.2"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$artifactDir = Join-Path $repoRoot "artifacts\release"
$cacheDir = Join-Path $repoRoot ".evalgate-cache\trivy"
$sbomPath = Join-Path $artifactDir "eg-021-sbom.cdx.json"
$allScanPath = Join-Path $artifactDir "eg-021-scan-all.json"
$actionableScanPath = Join-Path $artifactDir "eg-021-scan-actionable.json"
$summaryPath = Join-Path $artifactDir "eg-021-supply-chain-summary.json"
$scannerImage = "aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969"

New-Item -ItemType Directory -Force -Path $artifactDir, $cacheDir | Out-Null

function Invoke-Docker {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Arguments -join ' ') failed with exit code $LASTEXITCODE."
    }
}

$imageId = (& docker image inspect $Image --format "{{.Id}}").Trim()
if ($LASTEXITCODE -ne 0 -or -not $imageId.StartsWith("sha256:")) {
    throw "Unable to inspect candidate image ID for $Image."
}

$artifactMount = "$($artifactDir):/work"
$cacheMount = "$($cacheDir):/root/.cache/trivy"
$socketMount = "/var/run/docker.sock:/var/run/docker.sock"
$dockerPrefix = @(
    "run", "--rm",
    "-v", $socketMount,
    "-v", $artifactMount,
    "-v", $cacheMount,
    $scannerImage
)

$scannerVersion = (& docker run --rm $scannerImage version).Trim()
if ($LASTEXITCODE -ne 0 -or $scannerVersion -notmatch "Version:\s+0\.74\.0") {
    throw "Pinned scanner did not report Trivy 0.74.0."
}

Invoke-Docker @(
    $dockerPrefix +
    @(
        "image", "--format", "cyclonedx",
        "--output", "/work/eg-021-sbom.cdx.json", $Image
    )
)
Invoke-Docker @(
    $dockerPrefix +
    @(
        "image", "--scanners", "vuln", "--severity", "HIGH,CRITICAL",
        "--exit-code", "0", "--format", "json",
        "--output", "/work/eg-021-scan-all.json", $Image
    )
)
Invoke-Docker @(
    $dockerPrefix +
    @(
        "image", "--scanners", "vuln", "--severity", "HIGH,CRITICAL",
        "--ignore-unfixed", "--exit-code", "1", "--format", "json",
        "--output", "/work/eg-021-scan-actionable.json", $Image
    )
)

$allScan = Get-Content -Raw -Path $allScanPath | ConvertFrom-Json
$actionableScan = Get-Content -Raw -Path $actionableScanPath | ConvertFrom-Json
$allFindings = @(
    $allScan.Results |
        ForEach-Object { if ($_.PSObject.Properties["Vulnerabilities"]) { $_.Vulnerabilities } } |
        Where-Object { $null -ne $_ -and $_.Severity -in @("HIGH", "CRITICAL") }
)
$actionableFindings = @(
    $actionableScan.Results |
        ForEach-Object { if ($_.PSObject.Properties["Vulnerabilities"]) { $_.Vulnerabilities } } |
        Where-Object { $null -ne $_ -and $_.Severity -in @("HIGH", "CRITICAL") }
)
$upstreamUnfixedFindings = @(
    $allFindings |
        Where-Object { $null -eq $_.PSObject.Properties["FixedVersion"] -or -not $_.FixedVersion }
)
if ($actionableFindings.Count -ne 0) {
    throw "Candidate image has $($actionableFindings.Count) fixable HIGH/CRITICAL finding(s)."
}

@{
    schema_version = "1.0"
    story = "EG-021"
    image = $Image
    image_id = $imageId
    policy = @{
        enforcement = "fail_on_fixable_high_or_critical"
        disclosure = "retain_all_high_or_critical_findings"
        upstream_unfixed_is_not_described_as_clean = $true
    }
    scanner = @{
        name = "Trivy"
        version = "0.74.0"
        image = $scannerImage
        identity_output = $scannerVersion
    }
    sbom = @{
        path = "artifacts/release/eg-021-sbom.cdx.json"
        format = "CycloneDX JSON"
        sha256 = (Get-FileHash -Algorithm SHA256 -Path $sbomPath).Hash.ToLowerInvariant()
        status = "generated_for_exact_image"
    }
    container_scan = @{
        actionable_path = "artifacts/release/eg-021-scan-actionable.json"
        actionable_sha256 = (
            Get-FileHash -Algorithm SHA256 -Path $actionableScanPath
        ).Hash.ToLowerInvariant()
        all_findings_path = "artifacts/release/eg-021-scan-all.json"
        all_findings_sha256 = (
            Get-FileHash -Algorithm SHA256 -Path $allScanPath
        ).Hash.ToLowerInvariant()
        severities = @("HIGH", "CRITICAL")
        actionable_findings = $actionableFindings.Count
        upstream_unfixed_findings = $upstreamUnfixedFindings.Count
        disclosed_findings = $allFindings.Count
        status = "passed_actionable_gate_with_upstream_risk_disclosed"
    }
    secret_scan = @{
        command = "python scripts/check_publication.py"
        status = "covered_by_repository_check"
    }
    license_and_metadata_scan = @{
        command = "python scripts/check_metadata.py"
        status = "covered_by_repository_check"
    }
    publication = "not_pushed_not_deployed"
} | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -Path $summaryPath

Write-Host "Wrote pinned actionable and all-findings evidence to $summaryPath"
