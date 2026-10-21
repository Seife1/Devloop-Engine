#!/usr/bin/env python3
"""
LearnLoop Standalone Binary Builder.
Builds a single, zero-dependency executable for Windows, macOS, or Linux using PyInstaller.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root_dir = Path(__file__).resolve().parent.parent
    src_dir = root_dir / "src"
    entry_point = src_dir / "learnloop" / "cli.py"

    if not entry_point.exists():
        sys.stderr.write(f"Error: Entry point {entry_point} not found.\n")
        return 1

    print(f"=== Building Standalone LearnLoop Binary ===")
    print(f"Repository Root: {root_dir}")
    print(f"Entry Point:     {entry_point}")

    sep = os.pathsep

    # Static data files to package inside the single binary
    datas = [
        f"{src_dir / 'learnloop' / 'dashboard' / 'static' / 'app.css'}{sep}learnloop/dashboard/static",
        f"{src_dir / 'learnloop' / 'persistence' / 'migrations'}{sep}learnloop/persistence/migrations",
        f"{src_dir / 'learnloop' / 'taxonomy' / 'skills.yaml'}{sep}learnloop/taxonomy",
    ]

    hidden_imports = [
        "aiosqlite",
        "mcp",
        "mcp.server",
        "mcp.server.fastmcp",
        "platformdirs",
        "yaml",
        "sqlite3",
        "learnloop",
        "learnloop.cli",
        "learnloop.config",
        "learnloop.logging",
        "learnloop.server",
        "learnloop.gui",
        "learnloop.integrator",
        "learnloop.dashboard.server",
        "learnloop.dashboard.markdown",
        "learnloop.persistence.db",
        "learnloop.persistence.async_db",
        "learnloop.persistence.db_resilience",
        "learnloop.persistence.migrations.migration_014_mcp_native_helpers",
        "learnloop.taxonomy.loader",
    ]

    excludes = [
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "torch",
        "scipy",
        "PIL",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "learnloop",
        "--onefile",
        "--clean",
        "--paths",
        str(src_dir),
    ]

    for d in datas:
        cmd.extend(["--add-data", d])

    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])

    for ex in excludes:
        cmd.extend(["--exclude-module", ex])

    try:
        import webview  # noqa: F401

        cmd.extend(["--collect-all", "webview"])
    except ImportError:
        pass

    cmd.append(str(entry_point))

    print("\nRunning PyInstaller command:")
    print(" ".join(cmd[:8]), "... [truncated]")

    ret = subprocess.run(cmd, cwd=str(root_dir))
    if ret.returncode != 0:
        sys.stderr.write("Build failed!\n")
        return ret.returncode

    exe_name = "learnloop.exe" if sys.platform == "win32" else "learnloop"
    built_path = root_dir / "dist" / exe_name

    if built_path.exists():
        size_mb = built_path.stat().st_size / (1024 * 1024)
        print(f"\n[SUCCESS] Standalone binary built successfully!")
        print(f"Path: {built_path}")
        print(f"Size: {size_mb:.2f} MB")

        print("\nVerifying built binary execution:")
        test_run = subprocess.run([str(built_path), "doctor"], capture_output=True, text=True)
        print(f"Exit code: {test_run.returncode}")
        if test_run.stderr:
            print(f"Stderr: {test_run.stderr.strip()}")
        if test_run.stdout:
            print(f"Stdout: {test_run.stdout.strip()}")
        return 0
    else:
        sys.stderr.write(f"Expected binary {built_path} not found.\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
