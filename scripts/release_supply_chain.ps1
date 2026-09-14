param(
    [string]$Image = "evalgate-api:0.10.0"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$artifactDir = Join-Path $repoRoot "artifacts\release"
$sbomPath = Join-Path $artifactDir "eg-013d-sbom.cdx.json"
$scanPath = Join-Path $artifactDir "eg-013d-scan.json"
$summaryPath = Join-Path $artifactDir "eg-013d-supply-chain-summary.json"

New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

function Get-ToolPath {
    param([Parameter(Mandatory = $true)][string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        return $null
    }
    return $command.Source
}

$syft = Get-ToolPath "syft"
$trivy = Get-ToolPath "trivy"
$grype = Get-ToolPath "grype"
$docker = Get-ToolPath "docker"

$sbomStatus = "waived_tool_unavailable"
$scanStatus = "waived_tool_unavailable"

if ($null -ne $syft) {
    & syft $Image -o cyclonedx-json=$sbomPath
    if ($LASTEXITCODE -ne 0) {
        throw "syft SBOM generation failed with exit code $LASTEXITCODE."
    }
    $sbomStatus = "generated_cyclonedx_with_syft"
} elseif ($null -ne $docker) {
    & docker sbom $Image --format cyclonedx-json --output $sbomPath --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "docker sbom generation failed with exit code $LASTEXITCODE."
    }
    $sbomStatus = "generated_cyclonedx_with_docker_sbom"
} else {
    @{
        schema_version = "1.0"
        story = "EG-013D"
        format = "CycloneDX"
        status = "waived_tool_unavailable"
        disposition = "Install syft or Docker SBOM locally before release review."
    } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $sbomPath
}

if ($null -ne $trivy) {
    & trivy image --format json --output $scanPath $Image
    if ($LASTEXITCODE -ne 0) {
        throw "trivy image scan failed with exit code $LASTEXITCODE."
    }
    $scanStatus = "generated_with_trivy"
} elseif ($null -ne $grype) {
    & grype $Image -o json --file $scanPath
    if ($LASTEXITCODE -ne 0) {
        throw "grype image scan failed with exit code $LASTEXITCODE."
    }
    $scanStatus = "generated_with_grype"
} else {
    @{
        schema_version = "1.0"
        story = "EG-013D"
        status = "waived_tool_unavailable"
        disposition = "Install trivy or grype locally before release review; do not label this waiver as a vulnerability scan."
    } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $scanPath
}

@{
    schema_version = "1.0"
    story = "EG-013D"
    image = $Image
    sbom = @{
        path = "artifacts/release/eg-013d-sbom.cdx.json"
        status = $sbomStatus
    }
    container_scan = @{
        path = "artifacts/release/eg-013d-scan.json"
        status = $scanStatus
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

Write-Host "Wrote supply-chain evidence summary to $summaryPath"
