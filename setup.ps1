# LearnLoop One-Shot Universal Installer for Windows
# Usage: irm https://learnloop.dev/setup.ps1 | iex
# Or run locally: .\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ================================================================" -ForegroundColor Cyan
Write-Host "                LEARNLOOP - AI LEARNING COMPANION                 " -ForegroundColor White
Write-Host "              Zero Telemetry  *  100% Local-First                 " -ForegroundColor DarkGray
Write-Host "  ================================================================" -ForegroundColor Cyan
Write-Host ""

$binDir = Join-Path $env:USERPROFILE ".learnloop\bin"
if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

$exePath = Join-Path $binDir "learnloop.exe"
$localDist = Join-Path $PSScriptRoot "dist\learnloop.exe"

if (Test-Path $localDist) {
    Write-Host "[1/4] Using locally built binary from dist..." -ForegroundColor Yellow
    Copy-Item -Path $localDist -Destination $exePath -Force
} else {
    Write-Host "[1/4] Downloading standalone binary for Windows (x64)..." -ForegroundColor Cyan
    $releaseUrl = "https://github.com/seife1/learnloop/releases/latest/download/learnloop-windows-x64.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $releaseUrl -OutFile $exePath -UseBasicParsing
    } catch {
        Write-Host "  Note: GitHub Release binary not yet reached, checking local paths..." -ForegroundColor DarkGray
        if (-not (Test-Path $exePath)) {
            Write-Host "  Error downloading binary: $_" -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host "  [OK] Installed executable to $exePath" -ForegroundColor Green

# Add to User PATH if missing
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
    $env:Path = "$env:Path;$binDir"
    Write-Host "  [OK] Added ~/.learnloop/bin to User PATH" -ForegroundColor Green
}

# Run init and auto-integration in current repository
Write-Host "[2/4] Initializing LearnLoop & local SQLite database..." -ForegroundColor Cyan
& $exePath init --integrate

Write-Host "[3/4] Ingesting AI Companion rules into current project..." -ForegroundColor Cyan
Write-Host "  [OK] AGENTS.md, .cursorrules & .windsurfrules ready" -ForegroundColor Green

Write-Host "[4/4] Verification check..." -ForegroundColor Cyan
& $exePath doctor

Write-Host ""
Write-Host "  +-------------------------------------------------------------+" -ForegroundColor Green
Write-Host "  |                 INSTALLATION COMPLETE                       |" -ForegroundColor Green
Write-Host "  +-------------------------------------------------------------+" -ForegroundColor Green
Write-Host "  * IDEs Configured: Cursor, VS Code, Windsurf, Claude, Zed" -ForegroundColor White
Write-Host "  * Git Tracking:    Automatic via non-blocking post-commit hook" -ForegroundColor White
Write-Host "  * Privacy:         100% Local SQLite - Zero telemetry sent    " -ForegroundColor White
Write-Host "  * Dashboard:       Run 'learnloop dashboard' to launch UI     " -ForegroundColor Cyan
Write-Host "  +-------------------------------------------------------------+" -ForegroundColor Green
Write-Host ""
