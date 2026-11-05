# LearnLoop One-Shot Universal Installer for Windows
# Usage: irm https://learnloop.seife.workers.dev/setup.ps1 | iex
# Or run locally: .\setup.ps1

$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

$arch = if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
$psVer = "$($PSVersionTable.PSVersion.Major).$($PSVersionTable.PSVersion.Minor)"

Write-Host ""
Write-Host "  ================================================================" -ForegroundColor Cyan
Write-Host "        LEARNLOOP - AI LEARNING COMPANION  [GHOST MODE]          " -ForegroundColor White
Write-Host "             Zero Telemetry  *  100% Local-First                 " -ForegroundColor DarkGray
Write-Host "  ================================================================" -ForegroundColor Cyan
Write-Host "  Platform: Windows $arch (PowerShell $psVer)" -ForegroundColor DarkGray
Write-Host ""

# Detect installed editors/IDEs
$detectedEditors = @()
if ((Test-Path (Join-Path $env:APPDATA "Cursor")) -or (Test-Path (Join-Path $env:USERPROFILE ".cursor"))) {
    $detectedEditors += "Cursor"
}
if ((Test-Path (Join-Path $env:APPDATA "Code")) -or (Test-Path (Join-Path $env:USERPROFILE ".vscode"))) {
    $detectedEditors += "VS Code"
}
if ((Test-Path (Join-Path $env:APPDATA "Windsurf")) -or (Test-Path (Join-Path $env:USERPROFILE ".windsurf"))) {
    $detectedEditors += "Windsurf"
}
if (Test-Path (Join-Path $env:APPDATA "Claude")) {
    $detectedEditors += "Claude Desktop"
}
if ((Test-Path (Join-Path $env:APPDATA "Zed")) -or (Test-Path (Join-Path $env:USERPROFILE ".zed"))) {
    $detectedEditors += "Zed"
}

if ($detectedEditors.Count -gt 0) {
    $editorsStr = $detectedEditors -join ", "
    Write-Host "  -> Detected Editors: $editorsStr (ready for zero-config MCP)" -ForegroundColor Yellow
    Write-Host ""
}

$binDir = Join-Path $env:USERPROFILE ".learnloop\bin"
if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

$exePath = Join-Path $binDir "learnloop.exe"
$localDist = if ($PSScriptRoot) { Join-Path $PSScriptRoot "dist\learnloop.exe" } else { $null }

$installed = $false

if ($localDist -and (Test-Path $localDist)) {
    Write-Host "[1/3] Using locally built binary from dist..." -ForegroundColor Cyan
    Copy-Item -Path $localDist -Destination $exePath -Force
    $installed = $true
} else {
    Write-Host "[1/3] Standalone binary & environment check (Windows $arch)..." -ForegroundColor Cyan
    $releaseUrl = "https://github.com/Seife1/Devloop-Engine/releases/latest/download/learnloop-windows-x64.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $releaseUrl -OutFile $exePath -UseBasicParsing -ErrorAction Stop
        Write-Host "      [OK] Downloaded standalone binary" -ForegroundColor Green
        $installed = $true
    } catch {
        # Fall back to package engine silently
    }
}

if (-not $installed) {
    Write-Host "[1/3] Setting up environment..." -ForegroundColor Cyan
    $pyInstalled = $false

    # 1. Primary: If uv is installed, use it
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "[2/3] Installing LearnLoop engine (fetching packages, ~15s)..." -ForegroundColor Cyan
        & uv tool install "git+https://github.com/Seife1/Devloop-Engine.git" --force --quiet
        if ($LASTEXITCODE -eq 0) {
            $pyInstalled = $true
            Write-Host "      [OK] LearnLoop installed successfully" -ForegroundColor Green
        }
    }

    # 2. Secondary: Bootstrap uv silently
    if (-not $pyInstalled) {
        Write-Host "      * Bootstrapping standalone package engine (uv)..." -ForegroundColor DarkGray
        try {
            Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression | Out-Null
            $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
            if (Get-Command uv -ErrorAction SilentlyContinue) {
                Write-Host "[2/3] Installing LearnLoop engine (fetching packages, ~15s)..." -ForegroundColor Cyan
                & uv tool install "git+https://github.com/Seife1/Devloop-Engine.git" --force --quiet
                if ($LASTEXITCODE -eq 0) {
                    $pyInstalled = $true
                    Write-Host "      [OK] LearnLoop installed successfully" -ForegroundColor Green
                }
            }
        } catch {
            # Skip to pip fallback
        }
    }

    # 3. Tertiary: Fallback to pip / python only if uv failed
    if (-not $pyInstalled) {
        Write-Host "[2/3] Installing LearnLoop via package fallback..." -ForegroundColor Cyan
        if (Get-Command pip -ErrorAction SilentlyContinue) {
            & pip install --user "git+https://github.com/Seife1/Devloop-Engine.git" --quiet
            if ($LASTEXITCODE -eq 0) { $pyInstalled = $true }
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            $hasPip = & python -m pip --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                & python -m pip install --user "git+https://github.com/Seife1/Devloop-Engine.git" --quiet
                if ($LASTEXITCODE -eq 0) { $pyInstalled = $true }
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

# Add to User PATH if missing
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ([string]::IsNullOrWhiteSpace($userPath)) {
    [Environment]::SetEnvironmentVariable("Path", $binDir, "User")
    $env:Path = "$env:Path;$binDir"
} elseif ($userPath -notlike "*$binDir*") {
    $trimmed = $userPath.TrimEnd(";")
    [Environment]::SetEnvironmentVariable("Path", "$trimmed;$binDir", "User")
    $env:Path = "$env:Path;$binDir"
}

# Verification check
Write-Host "[3/3] Verifying installation & local database..." -ForegroundColor Cyan
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
$docOut = (& $exePath doctor 2>&1 | Out-String)
$ErrorActionPreference = $prevEap
if ($docOut -match "ok") {
    Write-Host "      [OK] Doctor check passed (local SQLite engine ready)" -ForegroundColor Green
} else {
    Write-Host $docOut
}

Write-Host ""
Write-Host "  +-------------------------------------------------------------+" -ForegroundColor Green
Write-Host "  |                 INSTALLATION COMPLETE                       |" -ForegroundColor Green
Write-Host "  +-------------------------------------------------------------+" -ForegroundColor Green
Write-Host "  * Executable:      $exePath" -ForegroundColor White
Write-Host "  * User PATH:       ~/.learnloop/bin permanently added" -ForegroundColor White
Write-Host "  * Architecture:    100% Local SQLite - Zero telemetry sent" -ForegroundColor White
if ($detectedEditors.Count -gt 0) {
    Write-Host "  * Detected IDEs:   $editorsStr (MCP ready)" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "  -> TO ACTIVATE IN THIS CURRENT TERMINAL:" -ForegroundColor Yellow
Write-Host "     `$env:Path = `"`$HOME\.learnloop\bin;`$env:Path`"" -ForegroundColor White
Write-Host ""
Write-Host "  -> QUICK START FOR NEW USERS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Verify engine & database:" -ForegroundColor Cyan
Write-Host "     learnloop doctor" -ForegroundColor White
Write-Host ""
Write-Host "  2. Connect to any project (Ghost Mode - 0 repo pollution):" -ForegroundColor Cyan
Write-Host "     cd \path\to\your\project" -ForegroundColor White
Write-Host "     learnloop init" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Open local learning dashboard:" -ForegroundColor Cyan
Write-Host "     learnloop dashboard   (or: learnloop gui)" -ForegroundColor White
Write-Host ""
Write-Host "  * In active projects: run 'learnloop briefing' or '/review' in IDE chat" -ForegroundColor DarkGray
Write-Host "  * Full command list:  learnloop --help" -ForegroundColor DarkGray
Write-Host "  * Clean uninstaller:  learnloop uninstall" -ForegroundColor DarkGray
Write-Host "  +-------------------------------------------------------------+" -ForegroundColor Green
Write-Host ""
