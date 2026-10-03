param(
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root "apps\api"
$web = Join-Path $root "apps\web"
$venv = Join-Path $api ".venv312\Scripts\Activate.ps1"

if (-not (Test-Path $venv)) {
    throw "API virtual environment not found. Create it first with: cd apps/api; python -m venv .venv"
}

docker compose -f (Join-Path $root "docker-compose.yml") up -d postgres redis

if ($Foreground) {
    Write-Host "Start these in separate terminals:" -ForegroundColor Cyan
    Write-Host "  cd $api; .\.venv\Scripts\Activate.ps1; python -m uvicorn main:app --reload --port 8000"
    Write-Host "  cd $api; .\.venv\Scripts\Activate.ps1; python -m worker"
    Write-Host "  cd $web; npm run dev"
    exit 0
}

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command", "Set-Location '$api'; & '$venv'; python -m uvicorn main:app --reload --port 8000"
)
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command", "Set-Location '$api'; & '$venv'; python -m worker"
)
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command", "Set-Location '$web'; npm run dev"
)

Write-Host "Started PostgreSQL, Redis, API, ingestion worker, and Next.js." -ForegroundColor Green
Write-Host "API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Web: http://localhost:3000" -ForegroundColor Cyan
