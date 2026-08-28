<#
.SYNOPSIS
    One-command dev startup for the Nexa Commerce API (Windows PowerShell).

.DESCRIPTION
    Creates the virtual environment and installs dependencies on first run,
    seeds the demo database if it is empty, then starts the API on port 8000.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Port 8080
    .\start.ps1 -Reseed
#>

[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$ApiHost = '127.0.0.1',
    [switch]$Reseed
)

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

Write-Host ''
Write-Host '  Nexa Commerce API' -ForegroundColor Cyan
Write-Host '  -----------------' -ForegroundColor DarkGray

# --- Locate a Python interpreter ------------------------------------------
$bootstrapPython = $null
foreach ($candidate in @('py', 'python3', 'python')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { $bootstrapPython = $cmd.Source; break }
}
if (-not $bootstrapPython) {
    Write-Host '  Python 3.10+ was not found on PATH. Install it from https://python.org' -ForegroundColor Red
    exit 1
}

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

# --- Create the venv on first run -----------------------------------------
if (-not (Test-Path $venvPython)) {
    Write-Host '  Creating virtual environment (.venv)...' -ForegroundColor Yellow
    & $bootstrapPython -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Host '  Could not create the virtual environment.' -ForegroundColor Red; exit 1 }

    Write-Host '  Installing dependencies...' -ForegroundColor Yellow
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Host '  Dependency installation failed.' -ForegroundColor Red; exit 1 }
}
else {
    # Cheap guard in case requirements changed since the venv was built.
    & $venvPython -c "import fastapi, uvicorn, sqlalchemy, jwt, pydantic_settings" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host '  Installing missing dependencies...' -ForegroundColor Yellow
        & $venvPython -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { Write-Host '  Dependency installation failed.' -ForegroundColor Red; exit 1 }
    }
}

# --- Seed the database ----------------------------------------------------
if ($Reseed) {
    Write-Host '  Rebuilding the demo dataset (--force)...' -ForegroundColor Yellow
    & $venvPython seed.py --force
}
elseif (-not (Test-Path (Join-Path $PSScriptRoot 'nexa.db'))) {
    Write-Host '  Seeding the demo dataset...' -ForegroundColor Yellow
    & $venvPython seed.py --force
}

# --- Run ------------------------------------------------------------------
Write-Host ''
Write-Host "  API    http://${ApiHost}:${Port}"       -ForegroundColor Green
Write-Host "  Docs   http://${ApiHost}:${Port}/docs"  -ForegroundColor Green
Write-Host ''
Write-Host '  Demo accounts' -ForegroundColor DarkGray
Write-Host '    admin     admin@nexa.com / Admin@123' -ForegroundColor DarkGray
Write-Host '    customer  demo@nexa.com / Demo@123'   -ForegroundColor DarkGray
Write-Host ''
Write-Host '  The frontend expects this API on http://localhost:8000' -ForegroundColor DarkGray
Write-Host '  Start it separately with:  cd ..\ep_frontend ; .\start.ps1' -ForegroundColor DarkGray
Write-Host ''
Write-Host '  Ctrl+C to stop.' -ForegroundColor DarkGray
Write-Host ''

& $venvPython run.py --host $ApiHost --port $Port
