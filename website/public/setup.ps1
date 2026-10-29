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

# Verification check
Write-Host "[2/2] Verifying installation..." -ForegroundColor Cyan
& $exePath doctor

Write-Host ""
Write-Host "  +-------------------------------------------------------------+" -ForegroundColor Green
Write-Host "  |                 INSTALLATION COMPLETE                       |" -ForegroundColor Green
Write-Host "  +-------------------------------------------------------------+" -ForegroundColor Green
Write-Host "  * Executable:      $exePath" -ForegroundColor White
Write-Host "  * User PATH:       ~/.learnloop/bin permanently added" -ForegroundColor White
Write-Host "  * Privacy:         100% Local SQLite - Zero telemetry sent    " -ForegroundColor White
Write-Host ""
Write-Host "  To initialize LearnLoop on any project, simply navigate to it:" -ForegroundColor Cyan
Write-Host "      cd /path/to/your/project" -ForegroundColor White
Write-Host "      learnloop init" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Available CLI commands inside initialized projects:" -ForegroundColor Cyan
Write-Host "      learnloop briefing    # Session catch-up" -ForegroundColor White
Write-Host "      learnloop review      # Spaced repetition check" -ForegroundColor White
Write-Host "      learnloop concepts    # View concepts catalog" -ForegroundColor White
Write-Host "      learnloop dashboard   # Launch local web dashboard" -ForegroundColor White
Write-Host "      learnloop gui         # Launch native desktop window" -ForegroundColor White
Write-Host "  +-------------------------------------------------------------+" -ForegroundColor Green
Write-Host ""
