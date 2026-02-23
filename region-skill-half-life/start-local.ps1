param(
    [string]$PythonExe = "",
    [int]$FrontendPort = 5500,
    [switch]$NoOpen,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
    param([string]$ExplicitPath)

    if ($ExplicitPath) {
        return $ExplicitPath
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return "py -3"
    }

    throw "Python executable not found. Install Python or pass -PythonExe <path>."
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

if (-not (Test-Path $backendDir)) {
    throw "Missing backend directory at: $backendDir"
}
if (-not (Test-Path $frontendDir)) {
    throw "Missing frontend directory at: $frontendDir"
}

$python = Resolve-Python -ExplicitPath $PythonExe

$backendCommand = "Set-Location '$backendDir'; $python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
$frontendCommand = "Set-Location '$frontendDir'; $python -m http.server $FrontendPort --bind 127.0.0.1"

if ($DryRun) {
    Write-Host "[DRY RUN] Backend command:"
    Write-Host $backendCommand
    Write-Host "[DRY RUN] Frontend command:"
    Write-Host $frontendCommand
    exit 0
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand | Out-Null
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand | Out-Null

Start-Sleep -Milliseconds 1200

if (-not $NoOpen) {
    Start-Process "http://127.0.0.1:$FrontendPort/login.html" | Out-Null
    Start-Process "http://127.0.0.1:8000/docs" | Out-Null
}

Write-Host "Backend started at http://127.0.0.1:8000"
Write-Host "Frontend started at http://127.0.0.1:$FrontendPort/login.html"
Write-Host "Use Ctrl+C in each spawned terminal to stop services."
