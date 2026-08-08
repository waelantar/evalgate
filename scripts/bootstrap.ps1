$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

foreach ($commandName in @("docker", "uv", "node", "npm")) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required command '$commandName' is not available on PATH."
    }
}

$nodeVersion = (node --version).Trim()
if ($LASTEXITCODE -ne 0) { throw "Node version check failed with exit code $LASTEXITCODE." }
if ($nodeVersion -ne "v24.19.0") {
    throw "Node.js 24.19.0 is required; found $nodeVersion."
}
$uvVersionOutput = (uv --version).Trim()
if ($LASTEXITCODE -ne 0) { throw "uv version check failed with exit code $LASTEXITCODE." }
$uvVersion = ($uvVersionOutput -split "\s+")[1]
if ($uvVersion -ne "0.12.3") {
    throw "uv 0.12.3 is required; found $uvVersionOutput."
}

docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw "Compose validation failed with exit code $LASTEXITCODE." }
docker compose up -d db
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL startup failed with exit code $LASTEXITCODE." }

Push-Location "apps/api"
try {
    uv sync --python 3.13.15 --locked
    if ($LASTEXITCODE -ne 0) { throw "Python dependency sync failed with exit code $LASTEXITCODE." }
} finally {
    Pop-Location
}

Push-Location "apps/web"
try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency install failed with exit code $LASTEXITCODE." }
} finally {
    Pop-Location
}

Write-Host "EvalGate foundation is ready. Start the API and web app using README.md."
