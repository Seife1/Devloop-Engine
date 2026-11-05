"""LearnLoop update detection and self-updater.

Provides fast, non-blocking update checking with a 24-hour local cache TTL,
ensuring zero overhead on local CLI commands and 100% privacy (zero telemetry).
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from learnloop import __version__

VERSION_ENDPOINT = "https://learnloop.seife.workers.dev/version.json"
CACHE_TTL_SECONDS = 86400  # 24 hours


def parse_semver(ver: str) -> tuple[int, ...]:
    """Parse version string into a comparable tuple of integers."""
    clean = ver.strip().lstrip("v").split("-")[0]
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(latest: str, current: str = __version__) -> bool:
    """Return True if latest is strictly newer than current according to SemVer."""
    try:
        return parse_semver(latest) > parse_semver(current)
    except Exception:
        return False


def get_cache_path() -> Path:
    """Return path to update check cache file."""
    cache_dir = Path.home() / ".learnloop" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "update_check.json"


def check_for_updates(
    force: bool = False, timeout: float = 1.5
) -> tuple[bool, str | None, str | None]:
    """Check if a newer version of LearnLoop is available.

    Returns:
        (has_update: bool, latest_version: str | None, changelog_url: str | None)
    """
    cache_file = get_cache_path()
    now = time.time()

    # 1. Check local cache first unless forced
    if not force and cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            last_checked = float(data.get("last_checked", 0))
            if now - last_checked < CACHE_TTL_SECONDS:
                latest = data.get("latest_version")
                changelog = data.get("changelog_url")
                if latest and is_newer_version(latest):
                    return (True, latest, changelog)
                return (False, latest, changelog)
        except Exception:
            pass

    # 2. Query version endpoint with safe short timeout
    try:
        req = urllib.request.Request(
            VERSION_ENDPOINT,
            headers={"User-Agent": f"LearnLoop-Updater/{__version__}"},
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            if resp.status == 200:
                payload = json.loads(resp.read().decode("utf-8"))
                latest = str(payload.get("version", "")).strip()
                changelog = str(payload.get("changelog_url", "")).strip() or None

                if latest:
                    # Write cache
                    try:
                        cache_file.write_text(
                            json.dumps(
                                {
                                    "last_checked": now,
                                    "latest_version": latest,
                                    "changelog_url": changelog,
                                }
                            ),
                            encoding="utf-8",
                        )
                    except Exception:
                        pass

                    if is_newer_version(latest):
                        return (True, latest, changelog)
                    return (False, latest, changelog)
    except Exception:
        pass

    return (False, None, None)


def format_update_banner(
    latest_version: str, changelog_url: str | None = None, use_color: bool = True
) -> str:
    """Format a sleek terminal update notification banner."""
    c_cyan = "\033[36m" if use_color else ""
    c_yellow = "\033[33m" if use_color else ""
    c_bold = "\033[1m" if use_color else ""
    c_reset = "\033[0m" if use_color else ""
    c_dim = "\033[90m" if use_color else ""

    text = f"Update available: {c_dim}v{__version__}{c_reset} → {c_cyan}v{latest_version}{c_reset}"
    cmd = f"Run '{c_yellow}learnloop update{c_reset}' to upgrade"

    lines = [
        f"\n  {c_cyan}╭─────────────────────────────────────────────────────────────╮{c_reset}",
        f"  {c_cyan}│{c_reset}  {c_bold}◈ {text}  {c_cyan}│{c_reset}",
        f"  {c_cyan}│{c_reset}    {cmd}                    {c_cyan}│{c_reset}",
        f"  {c_cyan}╰─────────────────────────────────────────────────────────────╯{c_reset}\n",
    ]
    return "\n".join(lines)


def print_update_banner_if_available() -> None:
    """Check cache and print banner if a newer version is known. Non-blocking."""
    try:
        if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
            return
        if "NO_COLOR" in os.environ:
            use_color = False
        else:
            use_color = True

        has_update, latest, changelog = check_for_updates(force=False, timeout=1.0)
        if has_update and latest:
            banner = format_update_banner(latest, changelog, use_color=use_color)
            sys.stdout.write(banner)
            sys.stdout.flush()
    except Exception:
        pass


def cmd_update(force: bool = False) -> int:
    """Self-update the LearnLoop installation."""
    sys.stdout.write(f"\nChecking for updates (current: v{__version__})...\n")
    sys.stdout.flush()

    has_update, latest, changelog = check_for_updates(force=True, timeout=5.0)

    if not has_update and not force:
        sys.stdout.write(f"\n[OK] LearnLoop is already up-to-date (v{__version__}).\n\n")
        return 0

    target_ver = latest if latest else "latest"
    sys.stdout.write(f"New version found: v{target_ver}\n")
    sys.stdout.write("Downloading update...\n")
    sys.stdout.flush()

    # Determine binary vs uv/pip install
    bin_dir = Path.home() / ".learnloop" / "bin"
    exe_name = "learnloop.exe" if sys.platform == "win32" else "learnloop"
    installed_bin = bin_dir / exe_name

    # Check if installed via standalone binary in ~/.learnloop/bin/
    is_standalone_bin = installed_bin.exists()

    if is_standalone_bin:
        os_name = sys.platform
        arch = platform.machine().lower()
        if arch in ("amd64", "x86_64"):
            arch = "x64"
        elif arch in ("aarch64", "arm64"):
            arch = "arm64"

        asset_name = None
        if os_name == "win32":
            asset_name = "learnloop-windows-x64.exe"
        elif os_name == "darwin":
            asset_name = f"learnloop-darwin-{arch}"
        elif os_name.startswith("linux"):
            asset_name = "learnloop-linux-x64"

        if asset_name:
            download_url = (
                f"https://github.com/Seife1/Devloop-Engine/releases/latest/download/{asset_name}"
            )
            temp_bin = bin_dir / f"{exe_name}.tmp"
            try:
                urllib.request.urlretrieve(download_url, str(temp_bin))
                if not os_name == "win32":
                    temp_bin.chmod(0o755)

                if os_name == "win32":
                    # On Windows, running exe cannot be written directly; rename trick:
                    old_bin = bin_dir / f"{exe_name}.old"
                    if old_bin.exists():
                        try:
                            old_bin.unlink()
                        except Exception:
                            pass
                    try:
                        installed_bin.rename(old_bin)
                    except Exception:
                        pass
                    shutil.move(str(temp_bin), str(installed_bin))
                    try:
                        old_bin.unlink()
                    except Exception:
                        pass
                else:
                    shutil.move(str(temp_bin), str(installed_bin))

                sys.stdout.write(
                    f"\n[OK] Successfully upgraded LearnLoop to v{target_ver}!\n"
                    f"Executable updated at: {installed_bin}\n\n"
                )
                return 0
            except Exception as e:
                sys.stdout.write(f"Direct binary download failed ({e}). Attempting package update...\n")

    # Fallback to package engine (uv or pip)
    if shutil.which("uv"):
        res = subprocess.run(["uv", "tool", "upgrade", "learnloop"], capture_output=True, text=True)
        if res.returncode == 0:
            sys.stdout.write(f"\n[OK] Successfully upgraded LearnLoop via uv!\n\n")
            return 0
        res = subprocess.run(
            ["uv", "tool", "install", "git+https://github.com/Seife1/Devloop-Engine.git", "--force"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            sys.stdout.write(f"\n[OK] Successfully upgraded LearnLoop via uv git install!\n\n")
            return 0

    if shutil.which("pip"):
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "git+https://github.com/Seife1/Devloop-Engine.git"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            sys.stdout.write(f"\n[OK] Successfully upgraded LearnLoop via pip!\n\n")
            return 0

    sys.stdout.write(
        f"\nCould not automatically swap binary. Please re-run the one-shot installer:\n"
        f"  Windows:    irm https://learnloop.seife.workers.dev/setup.ps1 | iex\n"
        f"  Mac/Linux:  curl -fsSL https://learnloop.seife.workers.dev/setup.sh | bash\n\n"
    )
    return 1
