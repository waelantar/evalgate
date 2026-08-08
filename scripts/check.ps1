$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

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

uv run --python 3.13.15 --project apps/api --locked python scripts/check_publication.py
if ($LASTEXITCODE -ne 0) { throw "Publication check failed with exit code $LASTEXITCODE." }
uv run --python 3.13.15 --project apps/api --locked python scripts/check_metadata.py
if ($LASTEXITCODE -ne 0) { throw "Metadata check failed with exit code $LASTEXITCODE." }
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw "Compose validation failed with exit code $LASTEXITCODE." }

Push-Location "apps/api"
try {
    uv run --python 3.13.15 --locked ruff format --check src tests
    if ($LASTEXITCODE -ne 0) { throw "Backend format check failed with exit code $LASTEXITCODE." }
    uv run --python 3.13.15 --locked ruff check src tests
    if ($LASTEXITCODE -ne 0) { throw "Backend lint failed with exit code $LASTEXITCODE." }
    uv run --python 3.13.15 --locked mypy src tests
    if ($LASTEXITCODE -ne 0) { throw "Backend type check failed with exit code $LASTEXITCODE." }
    uv run --python 3.13.15 --locked pytest
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed with exit code $LASTEXITCODE." }
} finally {
    Pop-Location
}

Push-Location "apps/web"
try {
    npm.cmd run lint
    if ($LASTEXITCODE -ne 0) { throw "Frontend lint failed with exit code $LASTEXITCODE." }
    npm.cmd run test
    if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed with exit code $LASTEXITCODE." }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed with exit code $LASTEXITCODE." }
} finally {
    Pop-Location
}
