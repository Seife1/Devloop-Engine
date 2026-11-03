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
$localDist = if ($PSScriptRoot) { Join-Path $PSScriptRoot "dist\learnloop.exe" } else { $null }

$installed = $false

if ($localDist -and (Test-Path $localDist)) {
    Write-Host "[1/4] Using locally built binary from dist..." -ForegroundColor Yellow
    Copy-Item -Path $localDist -Destination $exePath -Force
    $installed = $true
} else {
    Write-Host "[1/4] Downloading standalone binary for Windows (x64)..." -ForegroundColor Cyan
    $releaseUrl = "https://github.com/Seife1/Devloop-Engine/releases/latest/download/learnloop-windows-x64.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $releaseUrl -OutFile $exePath -UseBasicParsing
        $installed = $true
    } catch {
        Write-Host "  Notice: GitHub Release binary not yet reachable." -ForegroundColor DarkGray
    }
}

if (-not $installed) {
    Write-Host "  Falling back to direct Python/uv package engine..." -ForegroundColor Yellow
    $pyInstalled = $false

    # 1. Primary: If uv is installed, use it
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv tool install "git+https://github.com/Seife1/Devloop-Engine.git" --force
        $pyInstalled = $true
    }

    # 2. Secondary: Bootstrap uv (zero dependencies, works on any Windows machine)
    if (-not $pyInstalled) {
        Write-Host "  Bootstrapping ultra-fast standalone engine via uv..." -ForegroundColor Cyan
        try {
            irm https://astral.sh/uv/install.ps1 | iex
            $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
            if (Get-Command uv -ErrorAction SilentlyContinue) {
                & uv tool install "git+https://github.com/Seife1/Devloop-Engine.git" --force
                $pyInstalled = $true
            }
        } catch {
            Write-Host "  Notice: uv bootstrap skipped: $_" -ForegroundColor DarkGray
        }
    }

    # 3. Tertiary: Fallback to pip / python only if uv failed
    if (-not $pyInstalled) {
        if (Get-Command pip -ErrorAction SilentlyContinue) {
            & pip install --user "git+https://github.com/Seife1/Devloop-Engine.git"
            $pyInstalled = $true
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            $hasPip = & python -m pip --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                & python -m pip install --user "git+https://github.com/Seife1/Devloop-Engine.git"
                $pyInstalled = $true
            }
        }
    }

    if (-not $pyInstalled) {
        Write-Host "  Error: Could not install binary or bootstrap environment." -ForegroundColor Red
        exit 1
    }

    # Locate generated learnloop.exe and copy to $exePath
    $candidates = @(
        (Join-Path $env:USERPROFILE ".local\bin\learnloop.exe"),
        (Join-Path $env:APPDATA "Python\Scripts\learnloop.exe")
    )
    $found = $null
    foreach ($cand in $candidates) {
        if (Test-Path $cand) {
            $found = $cand
            break
        }
    }
    if (-not $found -and (Get-Command learnloop -ErrorAction SilentlyContinue)) {
        $found = (Get-Command learnloop).Source
    }
    if ($found -and (Test-Path $found)) {
        Copy-Item -Path $found -Destination $exePath -Force
    }
}

Write-Host "  [OK] Installed executable to $exePath" -ForegroundColor Green

# Add to User PATH if missing
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ([string]::IsNullOrWhiteSpace($userPath)) {
    [Environment]::SetEnvironmentVariable("Path", $binDir, "User")
    $env:Path = "$env:Path;$binDir"
    Write-Host "  [OK] Added ~/.learnloop/bin to User PATH" -ForegroundColor Green
} elseif ($userPath -notlike "*$binDir*") {
    $trimmed = $userPath.TrimEnd(";")
    [Environment]::SetEnvironmentVariable("Path", "$trimmed;$binDir", "User")
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
