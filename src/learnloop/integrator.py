#!/usr/bin/env python3
"""
LearnLoop Universal Integration System
Makes LearnLoop tools available in ANY IDE/terminal without manual file copying.
"""

import os
import sys

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import subprocess

class LearnLoopIntegrator:
    """Universal integration for all IDEs and terminals."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.learnloop_dir = self.project_root / ".learn"
        self.integrations_dir = Path(__file__).parent / "integrations"
        
        # IDE config locations
        self.ide_configs = {
            "vscode": [
                self.project_root / ".vscode" / "settings.json",
                Path.home() / ".vscode" / "settings.json",
            ],
            "cursor": [
                self.project_root / ".cursorrules",
                self.project_root / ".cursor" / "mcp.json",
                Path.home() / ".cursorrules",
            ],
            "claude": [
                self.project_root / "CLAUDE.md",
                self.project_root / ".claude.md",
            ],
            "windsurf": [
                self.project_root / ".windsurfrules",
                self.project_root / ".windsurf" / "mcp_config.json",
                Path.home() / ".windsurfrules",
            ],
            "zed": [
                self.project_root / ".zed" / "settings.json",
                self.project_root / "settings.json",
                Path.home() / ".config" / "zed" / "settings.json",
            ],
            "agents": [
                self.project_root / "AGENTS.md",
                self.project_root / "GEMINI.md",
            ],
            "any": [self.project_root / ".learnloop_rules.md"]
        }

    @staticmethod
    def _get_claude_desktop_config_path() -> Optional[Path]:
        """Return the platform-specific config path for Claude Desktop."""
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            return Path(appdata) / "Claude" / "claude_desktop_config.json" if appdata else None
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        else:
            return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    def detect_ide_status(self) -> Dict[str, Dict[str, Any]]:
        """Return rich detection status for each supported IDE."""
        # Cursor
        cursor_detected = (
            (self.project_root / ".cursor").exists()
            or (self.project_root / ".cursorrules").exists()
            or (Path.home() / ".cursor").exists()
            or bool(shutil.which("cursor"))
            or (sys.platform == "win32" and (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cursor").exists())
        )

        # VS Code
        vscode_detected = (
            (self.project_root / ".vscode").exists()
            or (Path.home() / ".vscode").exists()
            or bool(shutil.which("code"))
            or (sys.platform == "win32" and (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code").exists())
        )

        # Windsurf
        windsurf_detected = (
            (self.project_root / ".windsurf").exists()
            or (self.project_root / ".windsurfrules").exists()
            or (Path.home() / ".codeium" / "windsurf").exists()
            or bool(shutil.which("windsurf"))
            or (sys.platform == "win32" and (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Windsurf").exists())
        )

        # Claude Desktop / Code
        claude_cfg = self._get_claude_desktop_config_path()
        claude_detected = (
            (self.project_root / "CLAUDE.md").exists()
            or (claude_cfg is not None and claude_cfg.parent.exists())
            or bool(shutil.which("claude"))
        )

        # Zed
        zed_detected = (
            (self.project_root / ".zed").exists()
            or (Path.home() / ".config" / "zed").exists()
            or bool(shutil.which("zed"))
            or (sys.platform == "win32" and (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Zed").exists())
        )

        # Universal Agents (AGENTS.md / GEMINI.md)
        agents_detected = (
            (self.project_root / "AGENTS.md").exists()
            or (self.project_root / "GEMINI.md").exists()
            or True  # Universal - always recommended
        )

        return {
            "cursor": {
                "name": "Cursor",
                "desc": "Generates .cursorrules and configures MCP in .cursor/mcp.json",
                "detected": cursor_detected,
                "badge": "Detected" if cursor_detected else "Available",
            },
            "vscode": {
                "name": "VS Code",
                "desc": "Configures MCP in .vscode/settings.json",
                "detected": vscode_detected,
                "badge": "Detected" if vscode_detected else "Available",
            },
            "windsurf": {
                "name": "Windsurf",
                "desc": "Generates .windsurfrules and configures MCP",
                "detected": windsurf_detected,
                "badge": "Detected" if windsurf_detected else "Available",
            },
            "claude": {
                "name": "Claude Desktop & Code",
                "desc": "Configures claude_desktop_config.json and CLAUDE.md",
                "detected": claude_detected,
                "badge": "Detected" if claude_detected else "Available",
            },
            "zed": {
                "name": "Zed",
                "desc": "Configures MCP in .zed/settings.json",
                "detected": zed_detected,
                "badge": "Detected" if zed_detected else "Available",
            },
            "agents": {
                "name": "Antigravity & Universal AI Agents",
                "desc": "Generates AGENTS.md and GEMINI.md (Copilot, Roo, Cline, Aider)",
                "detected": agents_detected,
                "badge": "Recommended",
            },
        }

    def detect_ide(self) -> List[str]:
        """Detect which IDEs are being used."""
        status = self.detect_ide_status()
        detected = [k for k, v in status.items() if v["detected"]]
        if "any" not in detected:
            detected.append("any")
        return detected
    
    def get_mcp_config(self, ide: str) -> Dict[str, Any]:
        """Get MCP configuration for specific IDE."""
        return {
            "mcpServers": {
                "learnloop": {
                    "command": "learnloop",
                    "args": []
                }
            }
        }
    
    def generate_rules_content(self, ide: str = "generic") -> str:
        """Generate canonical LearnLoop rule content."""
        return """## LearnLoop (learning companion)

You are working with a learner who builds projects with AI and must be confident explaining each project. Use the `learnloop` MCP tools:

1. At session start: call `get_session_briefing`. Present the calm ~60s briefing, offer the ONE suggested next action, and honor "skip" or "not now". Overdue items are simply re-spaced.
2. For an architecture walkthrough or when onboarding to a project: call `get_project_tour` to guide the learner through entry points and components from basic to advanced.
3. Before implementing a meaningful piece of work: call `start_skill_session` with the files you plan to touch (`files: [...]`), a one-line summary, and WHY. Use a stable `intent_id` (e.g. a short slug) so retries don't duplicate.
4. When you choose between real alternatives: call `log_decision`.
5. NEVER log what you merely "did" as learning. Git commits are the proof of outcome (a hook records them). After the user commits, call `ingest_queue`.
6. When creating a component, making an architectural choice, or fixing a subtle bug: offer `register_knowledge_item` with key, title, summary, and tracked files.
7. When conducting spaced reviews or technical interviews: call `review_due`, ask ONE question at a time, wait for learner's answer, and record outcomes with `record_review`.
8. When introducing a new technology, scaling up architecture, or deciding on patterns: call `add_did_you_know` to record a captivating, sourced insight (living spec evolution/deprecations, creator origin lore, or pop culture/media crossovers like movies/anime/books).
"""
    
    def integrate_ide(self, ide: str, force: bool = False) -> bool:
        """Integrate LearnLoop with specific IDE."""
        print(f"Integrating with {ide.upper()}...")

        if ide == "agents":
            return self._integrate_agents_rules(force)
        
        if ide == "claude":
            return self._integrate_claude(force)

        if ide == "cursor":
            return self._integrate_cursor(force)

        if ide == "windsurf":
            return self._integrate_windsurf(force)
        
        # Get config paths for json-based IDEs (vscode, zed, any)
        config_paths = self.ide_configs.get(ide, [])
        
        for config_path in config_paths:
            if not config_path.parent.exists():
                config_path.parent.mkdir(parents=True, exist_ok=True)
            
            if ide in ["vscode", "zed"]:
                success = self._integrate_json_config(config_path, ide, force)
            elif ide == "any":
                success = self._integrate_generic_rules(config_path, force)
            else:
                success = False
            
            if success:
                print(f"  ✅ Integrated: {config_path}")
                return True
        
        print(f"  ❌ No suitable config location found for {ide}")
        return False

    def _integrate_agents_rules(self, force: bool) -> bool:
        """Integrate universal agent rules (AGENTS.md & GEMINI.md)."""
        rules = self.generate_rules_content("agents")
        for filename in ("AGENTS.md", "GEMINI.md"):
            p = self.project_root / filename
            self._write_rule_file(p, rules, force)
        return True

    def _integrate_claude(self, force: bool) -> bool:
        """Integrate Claude Desktop global config and project CLAUDE.md."""
        rules = self.generate_rules_content("claude")
        self._write_rule_file(self.project_root / "CLAUDE.md", rules, force)

        # Also configure Claude Desktop app if config dir exists or can be created
        desktop_cfg = self._get_claude_desktop_config_path()
        if desktop_cfg:
            try:
                desktop_cfg.parent.mkdir(parents=True, exist_ok=True)
                self._integrate_json_config(desktop_cfg, "claude", force)
            except Exception:
                pass
        return True

    def _integrate_cursor(self, force: bool) -> bool:
        """Integrate Cursor rules and MCP."""
        rules = self.generate_rules_content("cursor")
        self._write_rule_file(self.project_root / ".cursorrules", rules, force)

        # Also configure .cursor/mcp.json
        cursor_mcp = self.project_root / ".cursor" / "mcp.json"
        try:
            cursor_mcp.parent.mkdir(parents=True, exist_ok=True)
            self._integrate_json_config(cursor_mcp, "cursor", force)
        except Exception:
            pass
        return True

    def _integrate_windsurf(self, force: bool) -> bool:
        """Integrate Windsurf rules and MCP."""
        rules = self.generate_rules_content("windsurf")
        self._write_rule_file(self.project_root / ".windsurfrules", rules, force)

        # Configure .windsurf/mcp_config.json
        ws_mcp = self.project_root / ".windsurf" / "mcp_config.json"
        try:
            ws_mcp.parent.mkdir(parents=True, exist_ok=True)
            self._integrate_json_config(ws_mcp, "windsurf", force)
        except Exception:
            pass
        return True

    def _write_rule_file(self, path: Path, content: str, force: bool) -> bool:
        if path.exists() and not force:
            try:
                current = path.read_text(encoding="utf-8")
                if "LearnLoop" in current:
                    print(f"  ⚠️  LearnLoop already integrated: {path}")
                    return True
                path.write_text(current + "\n\n" + content, encoding="utf-8")
            except Exception:
                path.write_text(content, encoding="utf-8")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        print(f"  ✅ Integrated rules: {path}")
        return True
    
    def _integrate_json_config(self, config_path: Path, ide: str, force: bool) -> bool:
        """Integrate with JSON-based config (VS Code, Zed, Claude, Cursor)."""
        config = {}
        if config_path.exists() and not force:
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                print(f"  ⚠️  Config file corrupt, overwriting: {config_path}")
        
        mcp_config = self.get_mcp_config(ide)
        
        # Merge MCP config
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        
        config["mcpServers"].update(mcp_config["mcpServers"])
        
        # Write config
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return True
    
    def _integrate_generic_rules(self, config_path: Path, force: bool) -> bool:
        """Integrate with generic rules file."""
        return self._write_rule_file(config_path, self.generate_rules_content("generic"), force)
    
    def create_terminal_wrapper(self) -> bool:
        """Create terminal wrapper script for direct tool access."""
        # Ensure .learn directory exists
        self.learnloop_dir.mkdir(parents=True, exist_ok=True)
        
        wrapper_path = self.learnloop_dir / "tools.sh"
        
        wrapper_content = """#!/bin/bash
# LearnLoop Terminal Wrapper
# Access LearnLoop tools directly from terminal

LEARNLOOP_CMD="learnloop"

case "$1" in
    "briefing")
        echo "📋 Getting session briefing..."
        $LEARNLOOP_CMD briefing
        ;;
    "start-session")
        echo "🚀 Starting skill session..."
        shift
        $LEARNLOOP_CMD start_skill_session "$@"
        ;;
    "review")
        echo "📚 Starting review session..."
        $LEARNLOOP_CMD review
        ;;
    "register")
        echo "💡 Registering knowledge item..."
        shift
        $LEARNLOOP_CMD register-knowledge-item "$@"
        ;;
    "dashboard")
        echo "📊 Opening dashboard..."
        $LEARNLOOP_CMD dashboard &
        ;;
    "integrate")
        echo "🔧 Integrating with IDEs..."
        python -m learnloop.integrator "$@"
        ;;
    "help"|"")
        echo "LearnLoop Terminal Commands:"
        echo "  briefing      - Get session briefing"
        echo "  start-session - Start skill session (args: intent files)"
        echo "  review        - Start review session"
        echo "  register      - Register knowledge item"
        echo "  dashboard     - Open dashboard"
        echo "  integrate     - Integrate with IDEs"
        echo "  help         - Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use: learnloop-tools help"
        exit 1
        ;;
esac
"""
        
        wrapper_path.write_text(wrapper_content, encoding="utf-8")
        wrapper_path.chmod(0o755)
        
        # Create batch file for Windows
        batch_path = self.learnloop_dir / "tools.bat"
        batch_content = """@echo off
REM LearnLoop Terminal Wrapper for Windows

set LEARNLOOP_CMD=learnloop

if "%1"=="briefing" (
    echo 📋 Getting session briefing...
    %LEARNLOOP_CMD% briefing
) else if "%1"=="start-session" (
    echo 🚀 Starting skill session...
    shift
    %LEARNLOOP_CMD% start_skill_session %*
) else if "%1"=="review" (
    echo 📚 Starting review session...
    %LEARNLOOP_CMD% review
) else if "%1"=="register" (
    echo 💡 Registering knowledge item...
    shift
    %LEARNLOOP_CMD% register-knowledge-item %*
) else if "%1"=="dashboard" (
    echo 📊 Opening dashboard...
    start %LEARNLOOP_CMD% dashboard
) else if "%1"=="integrate" (
    echo 🔧 Integrating with IDEs...
    python -m learnloop.integrator %*
) else if "%1"=="" (
    goto :help
) else if "%1"=="help" (
    goto :help
) else (
    echo Unknown command: %1
    echo Use: learnloop-tools help
    exit /b 1
)

:help
echo LearnLoop Terminal Commands:
echo   briefing      - Get session briefing
echo   start-session - Start skill session ^(args: intent files^)
echo   review        - Start review session
echo   register      - Register knowledge item
echo   dashboard     - Open dashboard
echo   integrate     - Integrate with IDEs
echo   help         - Show this help
"""
        
        batch_path.write_text(batch_content, encoding="utf-8")
        
        print(f"  ✅ Terminal wrappers created:")
        print(f"     - {wrapper_path}")
        print(f"     - {batch_path}")
        print(f"  📝 Use: learnloop-tools [command]")
        
        return True
    
    def setup_environment(self) -> bool:
        """Set up environment for LearnLoop usage."""
        # Create .learn directory if it doesn't exist
        self.learnloop_dir.mkdir(exist_ok=True)
        
        # Create environment file
        env_path = self.learnloop_dir / "environment.sh"
        env_content = """# LearnLoop Environment Setup
export LEARNLOOP_PROJECT_ID="$(basename "$(pwd)")"
export LEARNLOOP_PROJECT_PATH="$(pwd)"
export PATH="$PATH:$(pwd)/.learn"

alias ll-briefing="learnloop briefing"
alias ll-review="learnloop review"
alias ll-dashboard="learnloop dashboard &"
"""
        
        env_path.write_text(env_content, encoding="utf-8")
        
        # Create PowerShell profile script
        ps_profile = self.learnloop_dir / "LearnLoop.ps1"
        ps_content = """# LearnLoop PowerShell Profile
$env:LEARNLOOP_PROJECT_ID = $(Get-Item .).Name
$env:LEARNLOOP_PROJECT_PATH = $(Get-Location).Path

function Get-LearnLoopBriefing {
    learnloop briefing
}

function Start-LearnLoopReview {
    learnloop review
}

function Open-LearnLoopDashboard {
    Start-Process -NoNewWindow learnloop dashboard
}

Set-Alias llb Get-LearnLoopBriefing
Set-Alias llr Start-LearnLoopReview
Set-Alias lld Open-LearnLoopDashboard
"""
        
        ps_profile.write_text(ps_content, encoding="utf-8")
        
        print("  ✅ Environment setup complete")
        print("  📝 Source: source .learn/environment.sh (Linux/Mac)")
        print("  📝 Or: . .\\learn\\LearnLoop.ps1 (Windows)")
        
        return True
    
    def run(self, args):
        """Run integration based on command line args."""
        parser = argparse.ArgumentParser(description="LearnLoop Universal Integration")
        parser.add_argument("--ide", choices=["auto", "vscode", "cursor", "claude", "windsurf", "zed", "agents", "all"], 
                          default="auto", help="IDE to integrate with")
        parser.add_argument("--force", action="store_true", help="Force overwrite existing configs")
        parser.add_argument("--terminal", action="store_true", help="Setup terminal integration")
        parser.add_argument("--env", action="store_true", help="Setup environment")
        parser.add_argument("--all", action="store_true", help="Setup everything")
        
        parsed_args = parser.parse_args(args)
        
        print("🔧 LearnLoop Universal Integration")
        print("=" * 40)
        
        # Setup everything if --all specified
        if parsed_args.all:
            parsed_args.terminal = True
            parsed_args.env = True
            parsed_args.ide = "all"
        
        # Detect IDEs
        if parsed_args.ide == "auto":
            detected_ides = self.detect_ide()
            print(f"📋 Detected IDEs: {', '.join(detected_ides)}")
            ides_to_integrate = detected_ides
        elif parsed_args.ide == "all":
            ides_to_integrate = list(self.ide_configs.keys())
        else:
            ides_to_integrate = [parsed_args.ide]
        
        # Integrate with IDEs
        for ide in ides_to_integrate:
            if ide != "any":  # Skip "any" in IDE integration
                self.integrate_ide(ide, parsed_args.force)
        
        # Setup terminal integration
        if parsed_args.terminal:
            print("\n🖥️  Setting up terminal integration...")
            self.create_terminal_wrapper()
        
        # Setup environment
        if parsed_args.env:
            print("\n🌍 Setting up environment...")
            self.setup_environment()
        
        print("\n✅ Integration Complete!")
        print("\n📋 Next Steps:")
        print("1. Restart your IDE for MCP config to take effect")
        print("2. Use: learnloop-tools [command] from terminal")
        print("3. Or use aliases: llb (briefing), llr (review), lld (dashboard)")
        print("4. Work with AI as usual - LearnLoop will track automatically")
        
        return True

def main():
    """Main entry point."""
    integrator = LearnLoopIntegrator()
    integrator.run(sys.argv[1:])

if __name__ == "__main__":
    main()


