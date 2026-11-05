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
    
    def __init__(self, project_root: Optional[Path] = None, in_repo: bool = False):
        from learnloop.config import get_workspace_storage_dir

        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.in_repo = in_repo
        self.quiet = False
        self.integrated_paths: list[Path] = []
        self.learnloop_dir = get_workspace_storage_dir(self.project_root)
        self.integrations_dir = Path(__file__).parent / "integrations"
        
        self._refresh_ide_configs()

    def _log(self, msg: str) -> None:
        if not getattr(self, "quiet", False):
            print(msg)

    def _refresh_ide_configs(self) -> None:
        """Refresh IDE configuration paths according to Ghost Mode vs In-Repo Mode."""
        if self.in_repo:
            self.ide_configs = {
                "vscode": [
                    self.project_root / ".vscode" / "settings.json",
                    self.project_root / ".vscode" / "mcp.json",
                ],
                "cursor": [
                    self.project_root / ".cursorrules",
                    self.project_root / ".cursor" / "mcp.json",
                ],
                "claude": [
                    self.project_root / "CLAUDE.md",
                ],
                "windsurf": [
                    self.project_root / ".windsurfrules",
                    self.project_root / ".windsurf" / "mcp_config.json",
                ],
                "zed": [
                    self.project_root / ".zed" / "settings.json",
                ],
                "agents": [
                    self.project_root / "AGENTS.md",
                    self.project_root / "GEMINI.md",
                ],
                "any": [self.project_root / ".learnloop_rules.md"]
            }
        else:
            self.ide_configs = {
                "vscode": self._get_vscode_user_settings_paths(),
                "cursor": [self._get_cursor_global_config_path()],
                "claude": [p for p in [self._get_claude_desktop_config_path()] if p],
                "windsurf": [self._get_windsurf_global_config_path()],
                "zed": [self._get_zed_global_config_path()],
                "agents": [Path.home() / ".learnloop" / "rules" / "AGENTS.md"],
                "any": [Path.home() / ".learnloop" / "rules" / ".learnloop_rules.md"]
            }

    @staticmethod
    def _get_vscode_user_settings_paths() -> List[Path]:
        """Return platform-specific user settings paths for VS Code and Insiders."""
        paths = []
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                paths.append(Path(appdata) / "Code" / "User" / "settings.json")
                paths.append(Path(appdata) / "Code - Insiders" / "User" / "settings.json")
            else:
                paths.append(Path.home() / "AppData" / "Roaming" / "Code" / "User" / "settings.json")
        elif sys.platform == "darwin":
            paths.append(Path.home() / "Library" / "Application Support" / "Code" / "User" / "settings.json")
            paths.append(Path.home() / "Library" / "Application Support" / "Code - Insiders" / "User" / "settings.json")
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME")
            base = Path(xdg) if xdg else Path.home() / ".config"
            paths.append(base / "Code" / "User" / "settings.json")
            paths.append(base / "Code - Insiders" / "User" / "settings.json")
        return paths

    @staticmethod
    def _get_vscode_cline_mcp_paths() -> List[Path]:
        """Return platform-specific global MCP settings paths for Cline and Roo Code extensions."""
        paths = []
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            base = Path(appdata) / "Code" / "User" / "globalStorage" if appdata else Path.home() / "AppData" / "Roaming" / "Code" / "User" / "globalStorage"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME")
            cfg = Path(xdg) if xdg else Path.home() / ".config"
            base = cfg / "Code" / "User" / "globalStorage"

        paths.append(base / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json")
        paths.append(base / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json")
        return paths

    @staticmethod
    def _get_cursor_global_config_path() -> Path:
        """Return user-level global Cursor MCP configuration path."""
        return Path.home() / ".cursor" / "mcp.json"

    @staticmethod
    def _get_windsurf_global_config_path() -> Path:
        """Return user-level global Windsurf MCP configuration path."""
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"

    @staticmethod
    def _get_zed_global_config_path() -> Path:
        """Return user-level global Zed configuration path."""
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "Zed" / "settings.json"
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
        return base / "zed" / "settings.json"

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

    def detect_active_ide(self) -> Optional[str]:
        """Detect the exact IDE hosting the current terminal session, or project marker."""
        env = os.environ
        term = env.get("TERM_PROGRAM", "").lower()
        cwd = env.get("VSCODE_CWD", "").lower()
        ipc = env.get("VSCODE_GIT_IPC_HANDLE", "").lower()

        # 1. Cursor terminal
        if (
            "cursor" in term
            or "cursor" in cwd
            or "cursor" in ipc
            or "CURSOR_TRACE_ID" in env
            or "CURSOR_VERSION" in env
        ):
            return "cursor"

        # 2. Windsurf terminal
        if (
            "windsurf" in term
            or "windsurf" in cwd
            or "windsurf" in ipc
            or "WINDSURF_VERSION" in env
        ):
            return "windsurf"

        # 3. Antigravity IDE terminal
        if "ANTIGRAVITY_AGENT" in env or "antigravity" in cwd:
            return "agents"

        # 4. VS Code terminal
        if term == "vscode" or "VSCODE_PID" in env or "microsoft vs code" in cwd or "code" in cwd:
            return "vscode"

        # 5. Zed terminal
        if "zed" in term or "ZED_TERM" in env:
            return "zed"

        # 6. Claude Code terminal
        if "CLAUDE_CODE" in env or "CLAUDE_PROJECT_DIR" in env:
            return "claude"

        # 7. Project-level marker files
        if (self.project_root / ".vscode").exists():
            return "vscode"
        if (self.project_root / ".cursor").exists() or (self.project_root / ".cursorrules").exists():
            return "cursor"
        if (self.project_root / ".windsurf").exists() or (self.project_root / ".windsurfrules").exists():
            return "windsurf"
        if (self.project_root / "CLAUDE.md").exists():
            return "claude"
        if (self.project_root / ".zed").exists():
            return "zed"
        if (self.project_root / "AGENTS.md").exists() or (self.project_root / "GEMINI.md").exists():
            return "agents"

        return None

    def detect_ide(self) -> List[str]:
        """Detect the specific active IDE for this terminal or project.
        
        Returns only the active IDE to avoid polluting projects with configs
        for editors the user is not actively working in.
        """
        active = self.detect_active_ide()
        if active:
            return [active]
        return ["agents"]

    
    @staticmethod
    def _resolve_command() -> str:
        """Resolve the safest executable command or path for the MCP server across OS platforms."""
        bin_name = "learnloop.exe" if sys.platform == "win32" else "learnloop"
        custom_bin = Path.home() / ".learnloop" / "bin" / bin_name
        try:
            if custom_bin.exists():
                return str(custom_bin)
        except (OSError, PermissionError):
            pass

        try:
            which_bin = shutil.which("learnloop")
            if which_bin:
                return which_bin
        except Exception:
            pass

        try:
            local_bin = Path.home() / ".local" / "bin" / bin_name
            if local_bin.exists():
                return str(local_bin)
        except (OSError, PermissionError):
            pass

        return "learnloop"

    def get_mcp_config(self, ide: str) -> Dict[str, Any]:
        """Get MCP configuration for specific IDE."""
        cmd = self._resolve_command()
        base_url = "http://127.0.0.1:8765"
        
        server_def: Dict[str, Any] = {
            "command": cmd,
            "args": ["serve"],
        }
        
        if ide in ("vscode", "cline", "roo"):
            server_def["type"] = "streamable-http"
            server_def["url"] = f"{base_url}/mcp"
        elif ide in ("cursor", "claude"):
            server_def["url"] = f"{base_url}/sse"
        elif ide == "windsurf":
            server_def["serverUrl"] = f"{base_url}/mcp"
        else:
            server_def["url"] = f"{base_url}/mcp"

        return {
            "mcpServers": {
                "learnloop": server_def
            }
        }
    
    def generate_rules_content(self, ide: str = "generic") -> str:
        """Generate canonical LearnLoop rule content."""
        return """## LearnLoop (learning companion)

You are working with a learner who builds projects with AI and must be confident explaining each project. LearnLoop uses 4 domain-clustered MCP tools (`project_id` is automatically resolved):

1. **Active Coding** (`track_intent`):
   - Before implementing meaningful work: call `track_intent(action="start_session", summary="...", files=[...])`.
   - When choosing between real technical alternatives: call `track_intent(action="log_decision", choice="...", alternatives=[...], tradeoffs="...")`.
   - After commits: call `track_intent(action="reconcile")`. NEVER log what you merely "did" as learning; git commits are the proof.
2. **Spaced Repetition & Catch-up** (`manage_reviews`):
   - At session start: call `manage_reviews(action="briefing")` for a calm catch-up briefing.
   - For reviews/interview prep: call `manage_reviews(action="due")`, ask ONE question at a time, and record outcomes with `manage_reviews(action="record", ...)`.
3. **Knowledge Catalog** (`manage_knowledge`):
   - When creating a component or fixing a subtle bug: call `manage_knowledge(action="register", key="...", title="...", kind="...", band="...", files=[...], summary="...")`.
   - To inspect concepts: call `manage_knowledge(action="list")` (compact by default).
4. **Codebase Exploration** (`explore_project`):
   - For codebase walkthroughs or onboarding: call `explore_project(action="tour")`.
   - When introducing new technologies: call `explore_project(action="add_fact", ...)` with a verified technical insight.
"""
    
    def integrate_ide(self, ide: str, force: bool = False) -> bool:
        """Integrate LearnLoop with specific IDE."""
        self._log(f"Integrating with {ide.upper()}...")

        if ide == "agents":
            return self._integrate_agents_rules(force)
        
        if ide == "claude":
            return self._integrate_claude(force)

        if ide == "cursor":
            return self._integrate_cursor(force)

        if ide == "windsurf":
            return self._integrate_windsurf(force)
        
        if ide == "vscode":
            return self._integrate_vscode(force)
        
        # Get config paths for json-based IDEs (zed, any)
        config_paths = self.ide_configs.get(ide, [])
        
        for config_path in config_paths:
            if not config_path.parent.exists():
                config_path.parent.mkdir(parents=True, exist_ok=True)
            
            if ide == "zed":
                success = self._integrate_json_config(config_path, ide, force)
            elif ide == "any":
                success = self._integrate_generic_rules(config_path, force)
            else:
                success = False
            
            if success:
                self.integrated_paths.append(config_path)
                self._log(f"  ✅ Integrated: {config_path}")
                return True
        
        self._log(f"  ❌ No suitable config location found for {ide}")
        return False

    def _integrate_vscode(self, force: bool) -> bool:
        """Integrate VS Code settings and MCP configuration."""
        if self.in_repo:
            settings_path = self.project_root / ".vscode" / "settings.json"
            self._integrate_json_config(settings_path, "vscode", force)
            self.integrated_paths.append(settings_path)
            self._log(f"  ✅ Integrated in-repo: {settings_path}")

            mcp_path = self.project_root / ".vscode" / "mcp.json"
            try:
                self._integrate_json_config(mcp_path, "vscode", force)
                self.integrated_paths.append(mcp_path)
                self._log(f"  ✅ Integrated in-repo: {mcp_path}")
            except Exception:
                pass
            return True

        # Ghost Mode (Zero Workspace Pollution): write to global user profile
        user_settings_paths = self._get_vscode_user_settings_paths()
        target_path = user_settings_paths[0]
        for p in user_settings_paths:
            if p.exists() or p.parent.exists():
                target_path = p
                break

        success = False
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            self._integrate_json_config(target_path, "vscode", force)
            self.integrated_paths.append(target_path)
            self._log(f"  ✅ Integrated global user config (Ghost Mode): {target_path}")
            success = True
        except Exception as exc:
            self._log(f"  ⚠️ Could not write to VS Code user settings {target_path}: {exc}")

        # Also configure Cline / Roo global MCP if those extensions are present
        for cline_p in self._get_vscode_cline_mcp_paths():
            if cline_p.parent.exists():
                try:
                    self._integrate_json_config(cline_p, "vscode", force)
                    self.integrated_paths.append(cline_p)
                    self._log(f"  ✅ Integrated global Cline/Roo MCP: {cline_p}")
                    success = True
                except Exception:
                    pass

        self._log("  💡 Tip: VS Code interacts with MCP via host extensions (GitHub Copilot, Cline, or Roo Code).")
        return success

    def _integrate_agents_rules(self, force: bool) -> bool:
        """Integrate universal agent rules (AGENTS.md & GEMINI.md)."""
        rules = self.generate_rules_content("agents")
        if self.in_repo:
            for filename in ("AGENTS.md", "GEMINI.md"):
                p = self.project_root / filename
                self._write_rule_file(p, rules, force)
                self.integrated_paths.append(p)
            return True

        # Ghost Mode: Store rules in user-level storage without polluting repository
        rules_dir = Path.home() / ".learnloop" / "rules"
        try:
            rules_dir.mkdir(parents=True, exist_ok=True)
            agents_p = rules_dir / "AGENTS.md"
            self._write_rule_file(agents_p, rules, force)
            self.integrated_paths.append(agents_p)
            self._log(f"  ✅ Stored universal agent instructions (Ghost Mode): {agents_p}")
            return True
        except Exception as exc:
            self._log(f"  ⚠️ Could not write agent rules: {exc}")
            return False

    def _integrate_claude(self, force: bool) -> bool:
        """Integrate Claude Desktop global config and project CLAUDE.md."""
        if self.in_repo:
            rules = self.generate_rules_content("claude")
            p = self.project_root / "CLAUDE.md"
            self._write_rule_file(p, rules, force)
            self.integrated_paths.append(p)

        # Global Claude Desktop app config
        desktop_cfg = self._get_claude_desktop_config_path()
        if desktop_cfg:
            try:
                desktop_cfg.parent.mkdir(parents=True, exist_ok=True)
                self._integrate_json_config(desktop_cfg, "claude", force)
                self.integrated_paths.append(desktop_cfg)
                self._log(f"  ✅ Integrated global Claude Desktop config (Ghost Mode): {desktop_cfg}")
                return True
            except Exception as exc:
                self._log(f"  ⚠️ Could not write Claude Desktop config: {exc}")
                return False
        return True

    def _integrate_cursor(self, force: bool) -> bool:
        """Integrate Cursor rules and MCP."""
        if self.in_repo:
            rules = self.generate_rules_content("cursor")
            p = self.project_root / ".cursorrules"
            self._write_rule_file(p, rules, force)
            self.integrated_paths.append(p)
            cursor_mcp = self.project_root / ".cursor" / "mcp.json"
            try:
                cursor_mcp.parent.mkdir(parents=True, exist_ok=True)
                self._integrate_json_config(cursor_mcp, "cursor", force)
                self.integrated_paths.append(cursor_mcp)
            except Exception:
                pass
            return True

        # Ghost Mode: Configure global user-level Cursor MCP
        cursor_global = self._get_cursor_global_config_path()
        try:
            cursor_global.parent.mkdir(parents=True, exist_ok=True)
            self._integrate_json_config(cursor_global, "cursor", force)
            self.integrated_paths.append(cursor_global)
            self._log(f"  ✅ Integrated global Cursor MCP (Ghost Mode): {cursor_global}")
            return True
        except Exception as exc:
            self._log(f"  ⚠️ Could not write Cursor global MCP: {exc}")
            return False

    def _integrate_windsurf(self, force: bool) -> bool:
        """Integrate Windsurf rules and MCP."""
        if self.in_repo:
            rules = self.generate_rules_content("windsurf")
            p = self.project_root / ".windsurfrules"
            self._write_rule_file(p, rules, force)
            self.integrated_paths.append(p)
            ws_mcp = self.project_root / ".windsurf" / "mcp_config.json"
            try:
                ws_mcp.parent.mkdir(parents=True, exist_ok=True)
                self._integrate_json_config(ws_mcp, "windsurf", force)
                self.integrated_paths.append(ws_mcp)
            except Exception:
                pass
            return True

        # Ghost Mode: Configure global Windsurf MCP
        ws_global = self._get_windsurf_global_config_path()
        try:
            ws_global.parent.mkdir(parents=True, exist_ok=True)
            self._integrate_json_config(ws_global, "windsurf", force)
            self.integrated_paths.append(ws_global)
            self._log(f"  ✅ Integrated global Windsurf MCP (Ghost Mode): {ws_global}")
            return True
        except Exception as exc:
            self._log(f"  ⚠️ Could not write Windsurf global MCP: {exc}")
            return False

    def _write_rule_file(self, path: Path, content: str, force: bool) -> bool:
        if path.exists() and not force:
            try:
                current = path.read_text(encoding="utf-8")
                if "LearnLoop" in current:
                    self._log(f"  ⚠️  LearnLoop already integrated: {path}")
                    return True
                path.write_text(current + "\n\n" + content, encoding="utf-8")
            except Exception:
                path.write_text(content, encoding="utf-8")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self._log(f"  ✅ Integrated rules: {path}")
        return True
    
    def _integrate_json_config(self, config_path: Path, ide: str, force: bool) -> bool:
        """Integrate with JSON-based config (VS Code, Zed, Claude, Cursor)."""
        config = {}
        if config_path.exists() and not force:
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._log(f"  ⚠️  Config file corrupt, overwriting: {config_path}")
        
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

    @staticmethod
    def _uninstall_from_json(config_path: Path) -> bool:
        """Remove 'learnloop' server entry from a JSON config file without touching any other servers."""
        try:
            if not config_path.exists():
                return False
        except (OSError, PermissionError):
            return False
        try:
            content = config_path.read_text(encoding="utf-8")
            data = json.loads(content)
            modified = False

            if "mcpServers" in data and isinstance(data["mcpServers"], dict):
                if "learnloop" in data["mcpServers"]:
                    del data["mcpServers"]["learnloop"]
                    modified = True

            if "context_servers" in data and isinstance(data["context_servers"], dict):
                if "learnloop" in data["context_servers"]:
                    del data["context_servers"]["learnloop"]
                    modified = True

            if modified:
                config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _strip_rule_file(path: Path) -> bool:
        """Remove LearnLoop rules from a rule file, or delete it if it only contained LearnLoop rules."""
        try:
            if not path.exists():
                return False
        except (OSError, PermissionError):
            return False
        try:
            content = path.read_text(encoding="utf-8")
            if "## LearnLoop (learning companion)" not in content and "# learnloop" not in content.lower():
                return False

            if ".learnloop" in str(path):
                path.unlink(missing_ok=True)
                return True

            lines = content.splitlines()
            filtered = []
            skip = False
            for line in lines:
                if line.strip().startswith("## LearnLoop (learning companion)"):
                    skip = True
                    continue
                if skip and line.startswith("## ") and not line.strip().startswith("## LearnLoop"):
                    skip = False
                if not skip:
                    filtered.append(line)

            remaining = "\n".join(filtered).strip()
            if not remaining:
                path.unlink(missing_ok=True)
            else:
                path.write_text(remaining + "\n", encoding="utf-8")
            return True
        except Exception:
            return False

    def uninstall_ide(self, ide: str) -> List[Path]:
        """Safely remove LearnLoop MCP configuration and rules for a specific IDE."""
        cleaned_paths = []
        if ide == "vscode":
            if self.in_repo:
                for p in (self.project_root / ".vscode" / "settings.json", self.project_root / ".vscode" / "mcp.json"):
                    if self._uninstall_from_json(p):
                        cleaned_paths.append(p)
            for p in self._get_vscode_user_settings_paths():
                if self._uninstall_from_json(p):
                    cleaned_paths.append(p)
            for p in self._get_vscode_cline_mcp_paths():
                if self._uninstall_from_json(p):
                    cleaned_paths.append(p)

        elif ide == "cursor":
            if self.in_repo:
                p_mcp = self.project_root / ".cursor" / "mcp.json"
                if self._uninstall_from_json(p_mcp):
                    cleaned_paths.append(p_mcp)
                p_rules = self.project_root / ".cursorrules"
                if self._strip_rule_file(p_rules):
                    cleaned_paths.append(p_rules)
            p_global = self._get_cursor_global_config_path()
            if self._uninstall_from_json(p_global):
                cleaned_paths.append(p_global)

        elif ide == "windsurf":
            if self.in_repo:
                p_mcp = self.project_root / ".windsurf" / "mcp_config.json"
                if self._uninstall_from_json(p_mcp):
                    cleaned_paths.append(p_mcp)
                p_rules = self.project_root / ".windsurfrules"
                if self._strip_rule_file(p_rules):
                    cleaned_paths.append(p_rules)
            p_global = self._get_windsurf_global_config_path()
            if self._uninstall_from_json(p_global):
                cleaned_paths.append(p_global)

        elif ide == "claude":
            if self.in_repo:
                p_rules = self.project_root / "CLAUDE.md"
                if self._strip_rule_file(p_rules):
                    cleaned_paths.append(p_rules)
            p_claude_desktop = self._get_claude_desktop_config_path()
            if p_claude_desktop and self._uninstall_from_json(p_claude_desktop):
                cleaned_paths.append(p_claude_desktop)

        elif ide == "zed":
            if self.in_repo:
                p_zed = self.project_root / ".zed" / "settings.json"
                if self._uninstall_from_json(p_zed):
                    cleaned_paths.append(p_zed)
            p_global = self._get_zed_global_config_path()
            if self._uninstall_from_json(p_global):
                cleaned_paths.append(p_global)

        elif ide == "agents":
            if self.in_repo:
                for fn in ("AGENTS.md", "GEMINI.md"):
                    p = self.project_root / fn
                    if self._strip_rule_file(p):
                        cleaned_paths.append(p)
            p_global = Path.home() / ".learnloop" / "rules" / "AGENTS.md"
            if self._strip_rule_file(p_global):
                cleaned_paths.append(p_global)

        elif ide == "any":
            for p in self.ide_configs.get("any", []):
                if self._strip_rule_file(p):
                    cleaned_paths.append(p)

        return cleaned_paths

    def uninstall_all(self) -> List[Path]:
        """Safely remove LearnLoop MCP configs and rules across all supported IDEs."""
        cleaned = []
        for ide in ("vscode", "cursor", "windsurf", "claude", "zed", "agents", "any"):
            cleaned.extend(self.uninstall_ide(ide))
        seen = set()
        deduped = []
        for p in cleaned:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        return deduped

    def run(self, args, quiet: bool = False):
        """Run integration based on command line args."""
        self.quiet = quiet
        parser = argparse.ArgumentParser(description="LearnLoop Universal Integration")
        parser.add_argument(
            "--ide",
            choices=["auto", "vscode", "cursor", "claude", "windsurf", "zed", "agents", "all"],
            default="auto",
            help="IDE to integrate with",
        )
        parser.add_argument("--force", action="store_true", help="Force overwrite existing configs")
        parser.add_argument("--all", action="store_true", help="Configure all supported IDEs")
        parser.add_argument(
            "--in-repo", action="store_true", help="Store configs in-repo rather than global user configs"
        )

        parsed_args = parser.parse_args(args)
        if parsed_args.in_repo:
            self.in_repo = True
            self._refresh_ide_configs()

        if not self.quiet:
            print("🔧 LearnLoop Universal Integration")
            print("=" * 40)

        # Setup everything if --all specified
        if parsed_args.all:
            parsed_args.ide = "all"

        # Detect IDEs
        if parsed_args.ide == "auto":
            detected_ides = self.detect_ide()
            if not self.quiet:
                ide_label = "IDE" if len(detected_ides) == 1 else "IDEs"
                print(f"📋 Detected {ide_label}: {', '.join(detected_ides)}")
            ides_to_integrate = detected_ides
        elif parsed_args.ide == "all":
            ides_to_integrate = list(self.ide_configs.keys())
        else:
            ides_to_integrate = [parsed_args.ide]

        # Integrate with IDEs
        for ide in ides_to_integrate:
            if ide != "any":  # Skip "any" in IDE integration
                self.integrate_ide(ide, parsed_args.force)

        if not self.quiet:
            print("\n✅ Integration Complete!")
            print("\n📋 Next Steps:")
            print("1. Restart your IDE for MCP config to take effect")
            print("2. Work with AI as usual - LearnLoop will track automatically")

        return {
            "success": True,
            "detected_ides": ides_to_integrate,
            "integrated_paths": list(dict.fromkeys(self.integrated_paths)),
        }

def main():
    """Main entry point."""
    integrator = LearnLoopIntegrator()
    integrator.run(sys.argv[1:])

if __name__ == "__main__":
    main()


