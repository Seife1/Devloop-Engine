#!/usr/bin/env python3
"""
LearnLoop Universal Integration System
Makes LearnLoop tools available in ANY IDE/terminal without manual file copying.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import subprocess

class LearnLoopIntegrator:
    """Universal integration for all IDEs and terminals."""
    
    def __init__(self):
        self.project_root = Path.cwd()
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
                Path.home() / ".cursorrules",
            ],
            "claude": [
                self.project_root / "CLAUDE.md",
                self.project_root / ".claude.md",
            ],
            "windsurf": [
                self.project_root / ".windsurfrules",
                Path.home() / ".windsurfrules",
            ],
            "zed": [
                self.project_root / "settings.json",
                Path.home() / ".config" / "zed" / "settings.json",
            ],
            "any": [self.project_root / ".learnloop_rules.md"]
        }
        
    def detect_ide(self) -> List[str]:
        """Detect which IDEs are being used."""
        detected = []
        
        # Check for IDE-specific files/directories
        if (self.project_root / ".vscode").exists():
            detected.append("vscode")
        if (self.project_root / ".cursorrules").exists():
            detected.append("cursor")
        if (self.project_root / "CLAUDE.md").exists() or (self.project_root / ".claude.md").exists():
            detected.append("claude")
        if (self.project_root / ".windsurfrules").exists():
            detected.append("windsurf")
        if (self.project_root / ".zed").exists() or (Path.home() / ".config" / "zed").exists():
            detected.append("zed")
        
        # Always include "any" for terminal usage
        detected.append("any")
        
        return detected
    
    def get_mcp_config(self, ide: str) -> Dict[str, Any]:
        """Get MCP configuration for specific IDE."""
        if ide in ["vscode", "zed"]:
            return {
                "mcpServers": {
                    "learnloop": {
                        "command": "learnloop",
                        "args": []
                    }
                }
            }
        elif ide == "cursor":
            return {
                "mcpServers": {
                    "learnloop": {
                        "command": "learnloop"
                    }
                }
            }
        else:
            # Generic MCP config
            return {
                "mcpServers": {
                    "learnloop": {
                        "command": "learnloop",
                        "args": []
                    }
                }
            }
    
    def generate_rules_content(self, ide: str) -> str:
        """Generate IDE-specific rules content."""
        template_path = self.integrations_dir / "rules" / f"{ide.upper()}.md.template"
        if template_path.exists():
            return template_path.read_text()
        
        # Fallback to generic template
        generic_path = self.integrations_dir / "rules" / "CLAUDE.md.template"
        if generic_path.exists():
            return generic_path.read_text()
        
        # Default rules
        return """## LearnLoop Integration

Use LearnLoop tools to track learning and build confidence:

1. **Session Start**: Call `get_session_briefing`
2. **Architecture**: Call `get_project_tour` 
3. **Work Session**: Call `start_skill_session`
4. **Decisions**: Call `log_decision`
5. **After Commits**: Call `ingest_queue`
6. **Knowledge**: Call `register_knowledge_item`
7. **Reviews**: Call `review_due` and `record_review`
8. **Insights**: Call `add_did_you_know`
"""
    
    def integrate_ide(self, ide: str, force: bool = False) -> bool:
        """Integrate LearnLoop with specific IDE."""
        print(f"Integrating with {ide.upper()}...")
        
        # Get config paths
        config_paths = self.ide_configs.get(ide, [])
        
        for config_path in config_paths:
            if not config_path.parent.exists():
                config_path.parent.mkdir(parents=True, exist_ok=True)
            
            if ide in ["vscode", "zed"]:
                success = self._integrate_json_config(config_path, ide, force)
            elif ide == "cursor":
                success = self._integrate_cursor_rules(config_path, force)
            elif ide == "claude":
                success = self._integrate_claude_rules(config_path, force)
            elif ide == "windsurf":
                success = self._integrate_windsurf_rules(config_path, force)
            elif ide == "any":
                success = self._integrate_generic_rules(config_path, force)
            
            if success:
                print(f"  ✅ Integrated: {config_path}")
                return True
        
        print(f"  ❌ No suitable config location found for {ide}")
        return False
    
    def _integrate_json_config(self, config_path: Path, ide: str, force: bool) -> bool:
        """Integrate with JSON-based config (VS Code, Zed)."""
        config = {}
        if config_path.exists() and not force:
            try:
                config = json.loads(config_path.read_text())
            except json.JSONDecodeError:
                print(f"  ⚠️  Config file corrupt, overwriting: {config_path}")
        
        mcp_config = self.get_mcp_config(ide)
        
        # Merge MCP config
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        
        config["mcpServers"].update(mcp_config["mcpServers"])
        
        # Write config
        config_path.write_text(json.dumps(config, indent=2))
        return True
    
    def _integrate_cursor_rules(self, config_path: Path, force: bool) -> bool:
        """Integrate with Cursor rules."""
        rules_content = self.generate_rules_content("cursor")
        
        if config_path.exists() and not force:
            current_content = config_path.read_text()
            if "LearnLoop" in current_content:
                print(f"  ⚠️  LearnLoop already integrated: {config_path}")
                return True
            
            # Append to existing rules
            new_content = current_content + "\n\n" + rules_content
            config_path.write_text(new_content)
        else:
            # Create new rules file
            config_path.write_text(rules_content)
        
        return True
    
    def _integrate_claude_rules(self, config_path: Path, force: bool) -> bool:
        """Integrate with Claude rules."""
        return self._integrate_text_rules(config_path, "claude", force)
    
    def _integrate_windsurf_rules(self, config_path: Path, force: bool) -> bool:
        """Integrate with WindSurf rules."""
        return self._integrate_text_rules(config_path, "windsurf", force)
    
    def _integrate_generic_rules(self, config_path: Path, force: bool) -> bool:
        """Integrate with generic rules file."""
        return self._integrate_text_rules(config_path, "any", force)
    
    def _integrate_text_rules(self, config_path: Path, ide: str, force: bool) -> bool:
        """Integrate with text-based rules files."""
        rules_content = self.generate_rules_content(ide)
        
        if config_path.exists() and not force:
            current_content = config_path.read_text()
            if "LearnLoop" in current_content:
                print(f"  ⚠️  LearnLoop already integrated: {config_path}")
                return True
            
            # Append to existing rules
            new_content = current_content + "\n\n" + rules_content
            config_path.write_text(new_content)
        else:
            # Create new rules file
            config_path.write_text(rules_content)
        
        return True
    
    def create_terminal_wrapper(self) -> bool:
        """Create terminal wrapper script for direct tool access."""
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
        
        wrapper_path.write_text(wrapper_content)
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
goto :eof

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
        
        batch_path.write_text(batch_content)
        
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
        
        env_path.write_text(env_content)
        
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
        
        ps_profile.write_text(ps_content)
        
        print("  ✅ Environment setup complete")
        print("  📝 Source: source .learn/environment.sh (Linux/Mac)")
        print("  📝 Or: . .\\learn\\LearnLoop.ps1 (Windows)")
        
        return True
    
    def run(self, args):
        """Run integration based on command line args."""
        parser = argparse.ArgumentParser(description="LearnLoop Universal Integration")
        parser.add_argument("--ide", choices=["auto", "vscode", "cursor", "claude", "windsurf", "zed", "all"], 
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
