#!/usr/bin/env python3
"""HTTP/SSE server for LearnLoop MCP plugin with proper MCP protocol support."""

import argparse
import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from mcp.server.fastmcp import FastMCP
from sse_starlette.sse import EventSourceResponse

from learnloop.config import Settings
from learnloop.server import build_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global MCP server instance
mcp_server: FastMCP | None = None
settings: Settings | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global mcp_server, settings
    
    # Startup
    logger.info("Starting LearnLoop HTTP server...")
    
    # Load settings
    settings = Settings.load()
    logger.info(f"Database path: {settings.db_path}")
    
    # Build MCP server
    mcp_server = build_server(settings)
    if hasattr(mcp_server, "settings") and hasattr(mcp_server.settings, "transport_security"):
        mcp_server.settings.transport_security.enable_dns_rebinding_protection = False
        if "*" not in mcp_server.settings.transport_security.allowed_hosts:
            mcp_server.settings.transport_security.allowed_hosts.append("*")
        if "*" not in mcp_server.settings.transport_security.allowed_origins:
            mcp_server.settings.transport_security.allowed_origins.append("*")
    logger.info("MCP server initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LearnLoop HTTP server...")
    mcp_server = None
    settings = None


# Create FastAPI app
app = FastAPI(
    title="LearnLoop HTTP Server",
    description="HTTP/SSE interface for LearnLoop MCP plugin",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with server information."""
    tools_count = 0
    if mcp_server:
        try:
            tools = await mcp_server.list_tools()
            tools_count = len(tools)
        except Exception as e:
            logger.error(f"Error getting tools count: {e}")
    
    return f"""
    <html>
        <head>
            <title>LearnLoop HTTP Server</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
                h1 {{ color: #333; }}
                .info {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .endpoint {{ background: #e8f4f8; padding: 10px; margin: 10px 0; border-left: 4px solid #3498db; }}
                code {{ background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h1>🚀 LearnLoop HTTP Server</h1>
            <div class="info">
                <p>Version: 1.0.0</p>
                <p>Status: Running</p>
                <p>Tools available: {tools_count}</p>
            </div>
            
            <h2>Endpoints</h2>
            <div class="endpoint">
                <strong>GET /health</strong> - Health check
            </div>
            <div class="endpoint">
                <strong>GET /mcp/v1/tools</strong> - MCP tools list (JSON-RPC)
            </div>
            <div class="endpoint">
                <strong>POST /mcp/v1/call</strong> - MCP tool calls (JSON-RPC)
            </div>
            <div class="endpoint">
                <strong>GET /sse</strong> - MCP SSE stream (for Devin/VSCode)
            </div>
            <div class="endpoint">
                <strong>GET /tools</strong> - REST tools list (legacy)
            </div>
            <div class="endpoint">
                <strong>POST /call/{{tool_name}}</strong> - REST tool calls (legacy)
            </div>
            
            <h2>Usage</h2>
            <p>For Devin/VSCode: <code>http://{os.getenv('LEARNLOOP_HTTP_HOST', 'localhost')}:{os.getenv('LEARNLOOP_HTTP_PORT', '8000')}/sse</code></p>
            <p>For direct API: <code>http://{os.getenv('LEARNLOOP_HTTP_HOST', 'localhost')}:{os.getenv('LEARNLOOP_HTTP_PORT', '8000')}/mcp/v1/tools</code></p>
            
            <h2>Documentation</h2>
            <p><a href="/docs">Interactive API docs (Swagger UI)</a></p>
            <p><a href="/redoc">Alternative API docs (ReDoc)</a></p>
        </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    tools_count = 0
    if mcp_server:
        try:
            tools = await mcp_server.list_tools()
            tools_count = len(tools)
        except Exception as e:
            logger.error(f"Error getting tools for health check: {e}")
    
    return {
        "status": "healthy",
        "service": "learnloop-http",
        "version": "1.0.0",
        "tools_available": tools_count,
        "database": str(settings.db_path) if settings else None,
        "mcp_endpoints": {
            "sse": "/sse",
            "tools": "/mcp/v1/tools",
            "call": "/mcp/v1/call"
        }
    }


@app.get("/tools")
async def list_tools_legacy():
    """Legacy REST endpoint for tools list."""
    if not mcp_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    try:
        tools_list = await mcp_server.list_tools()
        tools = []
        for tool in tools_list:
            schema = getattr(tool, "inputSchema", getattr(tool, "input_schema", {})) or {}
            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": schema,
                "inputSchema": schema,
            })
        
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Error in /tools endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/call/{tool_name}")
async def call_tool_legacy(tool_name: str, request: Request):
    """Legacy REST endpoint for tool calls."""
    if not mcp_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    try:
        body = {}
        raw = await request.body()
        if raw:
            body = await request.json()
        
        args = body.get("arguments", body) if isinstance(body, dict) else {}
        if not isinstance(args, dict):
            args = {}
        
        logger.info(f"Calling tool: {tool_name} with args: {args}")
        _, result = await mcp_server.call_tool(tool_name, args)
        
        return {
            "tool": tool_name,
            "result": result,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MCP Protocol Endpoints (for Devin/VSCode)
@app.get("/mcp/v1/tools")
async def mcp_list_tools():
    """MCP JSON-RPC tools listing endpoint."""
    if not mcp_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    try:
        tools_list = await mcp_server.list_tools()
        tools = []
        for tool in tools_list:
            schema = getattr(tool, "inputSchema", getattr(tool, "input_schema", {})) or {}
            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": schema,
            })
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": tools
            },
            "id": str(uuid.uuid4())
        }
    except Exception as e:
        logger.error(f"Error in MCP tools endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp")
async def mcp_streamable_get():
    """Information endpoint for /mcp."""
    return await mcp_list_tools()


@app.post("/mcp")
async def mcp_streamable_post(request: Request):
    """Handle Streamable HTTP JSON-RPC requests."""
    return await mcp_call_tool(request)


@app.post("/mcp/v1/call")
async def mcp_call_tool(request: Request):
    """MCP JSON-RPC tool calling and protocol endpoint."""
    if not mcp_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    try:
        # Parse JSON-RPC request
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        call_id = body.get("id", str(uuid.uuid4()))
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "LearnLoop HTTP Server",
                        "version": "1.0.0"
                    }
                },
                "id": call_id
            }
        
        if method == "notifications/initialized":
            return {
                "jsonrpc": "2.0",
                "result": {},
                "id": call_id
            }
        
        if method == "ping":
            return {
                "jsonrpc": "2.0",
                "result": {},
                "id": call_id
            }
        
        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "result": {"prompts": []},
                "id": call_id
            }
        
        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "result": {"resources": []},
                "id": call_id
            }
        
        if method == "tools/list":
            tools_list = await mcp_server.list_tools()
            tools = []
            for tool in tools_list:
                schema = getattr(tool, "inputSchema", getattr(tool, "input_schema", {})) or {}
                tools.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": schema,
                })
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": tools
                },
                "id": call_id
            }
        
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": "Missing tool name"
                    },
                    "id": call_id
                }
            
            # Call the tool via FastMCP server
            logger.info(f"MCP calling tool: {tool_name}")
            content_blocks, result = await mcp_server.call_tool(tool_name, arguments)
            
            content = []
            for block in content_blocks:
                if hasattr(block, "model_dump"):
                    content.append(block.model_dump())
                elif hasattr(block, "text"):
                    content.append({"type": "text", "text": block.text})
                else:
                    content.append({"type": "text", "text": str(block)})
            if not content:
                content = [{"type": "text", "text": json.dumps(result, default=str, indent=2)}]
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": content
                },
                "id": call_id
            }
        
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            },
            "id": call_id
        }
        
    except Exception as e:
        logger.error(f"Error in MCP call endpoint: {e}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            },
            "id": body.get("id", str(uuid.uuid4())) if 'body' in locals() else str(uuid.uuid4())
        }


@app.get("/sse")
async def mcp_sse_stream(request: Request):
    """MCP Server-Sent Events stream with proper protocol support."""
    if not mcp_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    async def event_generator():
        """Generate SSE events for MCP protocol."""
        # Send endpoint event first: points client to the POST message endpoint (REQUIRED for MCP)
        yield {
            "event": "endpoint",
            "data": "/mcp/v1/call"
        }
        
        # Initial connection message
        yield {
            "event": "message",
            "data": json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            })
        }
        
        # Keep connection alive
        while True:
            if await request.is_disconnected():
                logger.info("MCP SSE client disconnected")
                break
            
            # Send heartbeat
            yield {
                "event": "message",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "method": "notifications/heartbeat",
                    "params": {"timestamp": str(uuid.uuid4())}
                })
            }
            
            # Wait before next heartbeat
            import asyncio
            await asyncio.sleep(30)
    
    return EventSourceResponse(event_generator())


@app.get("/dashboard")
async def dashboard_redirect():
    """Redirect to the LearnLoop dashboard."""
    dashboard_port = os.getenv("LEARNLOOP_DASHBOARD_PORT", "8765")
    return {
        "redirect": f"http://localhost:{dashboard_port}",
        "message": "Dashboard is running on a different port",
    }


def get_agents_rules() -> str:
    agents_path = Path(__file__).parent / "AGENTS.md"
    if agents_path.exists():
        return agents_path.read_text("utf-8")
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


@app.get("/rules", response_class=PlainTextResponse)
async def get_rules():
    """Get the official LearnLoop AGENTS.md rules."""
    return get_agents_rules()


@app.post("/api/record-commit")
async def api_record_commit(request: Request):
    """Receive commit metadata from local or remote git post-commit hooks."""
    try:
        body = await request.json()
        sha = str(body.get("sha", "")).strip()
        if not sha:
            return JSONResponse(status_code=400, content={"error": "Missing sha"})
        
        message = str(body.get("message", ""))
        files_data = body.get("files", [])
        if isinstance(files_data, str):
            files = [f.strip() for f in files_data.split(",") if f.strip()]
        elif isinstance(files_data, list):
            files = [str(f).strip() for f in files_data if str(f).strip()]
        else:
            files = []
        
        from learnloop.domain import clock
        from learnloop.persistence.db import connect

        committed_at = str(body.get("committed_at", "")) or clock.iso(clock.utcnow())
        project_id = str(body.get("project_id", "")).strip()
        repo_name = str(body.get("repo", "default")).strip()
        
        conn = connect(settings.db_path)
        try:
            if not project_id:
                row = conn.execute("SELECT id FROM projects ORDER BY created_at ASC LIMIT 1").fetchone()
                project_id = row[0] if row else "default"
            
            from learnloop.capture.redaction import is_ignored, redact
            from learnloop.services.reconcile_service import reconcile
            
            clean_files = [f for f in files if isinstance(f, str) and not is_ignored(f)]
            clean_msg = redact(message)[:500]
            
            cur = conn.execute(
                "INSERT OR IGNORE INTO commits (sha, project_id, message, files, committed_at, origin, kind) "
                "VALUES (?, ?, ?, ?, ?, 'hook', 'commit')",
                (sha, project_id, clean_msg, json.dumps(clean_files), committed_at),
            )
            if cur.rowcount:
                import uuid
                conn.execute(
                    "INSERT OR IGNORE INTO queue_entries (id, project_id, commit_sha, processed, created_at) "
                    "VALUES (?, ?, ?, 0, ?)",
                    (str(uuid.uuid4()), project_id, sha, clock.iso(clock.utcnow())),
                )
            conn.commit()
            
            # Reconcile immediately so exposure and intent match on the fly!
            try:
                reconcile(conn, project_id)
            except Exception as r_err:
                logger.warning(f"Reconciliation note: {r_err}")
                
            logger.info(f"Successfully recorded remote commit {sha[:7]} for project {project_id}")
            return {"status": "ok", "sha": sha, "ingested": True}
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error recording remote commit: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/setup.ps1", response_class=PlainTextResponse)
async def get_setup_ps1(request: Request):
    """Dynamic one-line PowerShell setup script for remote Windows machines."""
    base_url = str(request.base_url).rstrip("/")
    sse_url = f"{base_url}/sse"
    commit_endpoint = f"{base_url}/api/record-commit"
    raw_rules = get_agents_rules()
    
    script = f'''# LearnLoop 1-Click Universal Integrator for Windows
Write-Host "=== LearnLoop One-Shot Integrator ===" -ForegroundColor Cyan
Write-Host "Connecting to LearnLoop Server at {base_url}..." -ForegroundColor Gray

# 1. Ingest official AGENTS.md rules into current project
$rulesContent = @'
{raw_rules}
'@
Set-Content -Path "AGENTS.md" -Value $rulesContent -Encoding utf8
Set-Content -Path ".windsurfrules" -Value $rulesContent -Encoding utf8
Write-Host "  [OK] Ingested AGENTS.md and .windsurfrules into current project" -ForegroundColor Green

# 2. Automatically install Git post-commit hook for zero-prompt commit tracking
if (Test-Path ".git") {{
    $hooksDir = ".git\\hooks"
    if (-not (Test-Path $hooksDir)) {{ New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null }}
    $hookFile = Join-Path $hooksDir "post-commit"
    $hookScript = @'
#!/bin/sh
# learnloop-hook: non-blocking commit reporter
(
  SHA=$(git rev-parse HEAD 2>/dev/null)
  [ -z "$SHA" ] && exit 0
  MSG=$(git log -1 --pretty=%s 2>/dev/null)
  COMMITTED=$(git log -1 --format=%cI 2>/dev/null)
  FILES=$(git diff-tree --no-commit-id --name-only -r --root HEAD 2>/dev/null | tr '\n' ',' | sed 's/,$//')
  
  curl -s -X POST "{commit_endpoint}" \
    -H "Content-Type: application/json" \
    -d "{{\\"sha\\":\\"$SHA\\",\\"message\\":\\"$MSG\\",\\"committed_at\\":\\"$COMMITTED\\",\\"files\\":\\"$FILES\\"}}" >/dev/null 2>&1
) &
exit 0
'@
    Set-Content -Path $hookFile -Value $hookScript -Encoding utf8
    Write-Host "  [OK] Installed Git post-commit hook (automatic tracking on every git commit)" -ForegroundColor Green
}}

# 3. Inject MCP server configuration into Windsurf
$windsurfPath = "$env:USERPROFILE\\.codeium\\windsurf\\mcp_config.json"
try {{
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($windsurfPath)) | Out-Null
    $cfg = if (Test-Path $windsurfPath) {{ Get-Content $windsurfPath -Raw | ConvertFrom-Json }} else {{ [pscustomobject]@{{}} }}
    if (-not $cfg.mcpServers) {{ $cfg | Add-Member -Name "mcpServers" -MemberType NoteProperty -Value ([pscustomobject]@{{}}) }}
    $mcpDef = [pscustomobject]@{{
        serverUrl = "{base_url}/mcp"
    }}
    $cfg.mcpServers | Add-Member -Name "learnloop" -MemberType NoteProperty -Value $mcpDef -Force
    $cfg | ConvertTo-Json -Depth 10 | Set-Content -Path $windsurfPath -Encoding utf8
    Write-Host "  [OK] Injected LearnLoop into Windsurf ($windsurfPath)" -ForegroundColor Green
}} catch {{
    Write-Host "  [!] Windsurf config update skipped: $_" -ForegroundColor Yellow
}}

# 4. Inject MCP into Devin Desktop if ~/.devin exists
$devinDir = "$env:USERPROFILE\\.devin"
$devinPath = "$devinDir\\mcp.json"
try {{
    if (Test-Path $devinDir) {{
        $dcfg = if (Test-Path $devinPath) {{ Get-Content $devinPath -Raw | ConvertFrom-Json }} else {{ [pscustomobject]@{{}} }}
        if (-not $dcfg.mcpServers) {{ $dcfg | Add-Member -Name "mcpServers" -MemberType NoteProperty -Value ([pscustomobject]@{{}}) }}
        $devinDef = [pscustomobject]@{{
            type = "streamable-http"
            url = "{base_url}/mcp"
        }}
        $dcfg.mcpServers | Add-Member -Name "learnloop" -MemberType NoteProperty -Value $devinDef -Force
        $dcfg | ConvertTo-Json -Depth 10 | Set-Content -Path $devinPath -Encoding utf8
        Write-Host "  [OK] Injected LearnLoop into Devin Desktop ($devinPath)" -ForegroundColor Green
    }}
}} catch {{
    Write-Host "  [!] Devin config update skipped: $_" -ForegroundColor Yellow
}}

# 5. Inject MCP into VS Code workspace if .vscode exists
if (Test-Path ".vscode") {{
    $vscodeSettings = ".vscode\\settings.json"
    try {{
        $vsc = if (Test-Path $vscodeSettings) {{ Get-Content $vscodeSettings -Raw | ConvertFrom-Json }} else {{ [pscustomobject]@{{}} }}
        if (-not $vsc.mcpServers) {{ $vsc | Add-Member -Name "mcpServers" -MemberType NoteProperty -Value ([pscustomobject]@{{}}) }}
        $vsc.mcpServers | Add-Member -Name "learnloop" -MemberType NoteProperty -Value $mcpDef -Force
        $vsc | ConvertTo-Json -Depth 10 | Set-Content -Path $vscodeSettings -Encoding utf8
        Write-Host "  [OK] Injected LearnLoop into VS Code ($vscodeSettings)" -ForegroundColor Green
    }} catch {{
        Write-Host "  [!] VS Code settings update skipped: $_" -ForegroundColor Yellow
    }}
}}

# 6. Visual & Audio Confirmation
try {{
    [System.Media.SystemSounds]::Asterisk.Play()
    $wshell = New-Object -ComObject WScript.Shell
    # 3-second auto-closing notification popup
    $wshell.Popup("LearnLoop is now connected!`n`n• Git commits track automatically`n• Rules ingested into AGENTS.md`n• Windsurf & VS Code configured`n`nRestart IDE or reload Cascade to start.", 3, "LearnLoop Companion Active", 64) | Out-Null
}} catch {{}}

Write-Host @"

  ╔═══════════════════════════════════════════════════════════════════╗
  ║                 LEARNLOOP INTEGRATION ACTIVE                      ║
  ║  • Server:      {base_url:<48}║
  ║  • Commits:     Tracking automatically via Git post-commit hook    ║
  ║  • IDEs:        Windsurf, Devin & VS Code (Direct HTTP / MCP)      ║
  ║  • Rules:       AGENTS.md & .windsurfrules ingested                ║
  ╚═══════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan
Write-Host "No manual AI prompting needed for commits! Just code and git commit." -ForegroundColor Green
'''
    return script


@app.get("/setup.sh", response_class=PlainTextResponse)
async def get_setup_sh(request: Request):
    """Dynamic one-line Bash setup script for remote Mac/Linux machines."""
    base_url = str(request.base_url).rstrip("/")
    sse_url = f"{base_url}/sse"
    commit_endpoint = f"{base_url}/api/record-commit"
    raw_rules = get_agents_rules()
    
    script = f'''#!/usr/bin/env bash
set -e
echo "=== LearnLoop One-Shot Integrator ==="
echo "Connecting to LearnLoop Server at {base_url}..."

# 1. Ingest official AGENTS.md rules into current project
cat << 'EOF' > AGENTS.md
{raw_rules}
EOF
cp AGENTS.md .windsurfrules 2>/dev/null || true
echo "  [OK] Ingested AGENTS.md and .windsurfrules into current project"

# 2. Automatically install Git post-commit hook
if [ -d ".git" ]; then
    mkdir -p .git/hooks
    cat << 'HOOKEOF' > .git/hooks/post-commit
#!/bin/sh
# learnloop-hook: non-blocking commit reporter
(
  SHA=$(git rev-parse HEAD 2>/dev/null)
  [ -z "$SHA" ] && exit 0
  MSG=$(git log -1 --pretty=%s 2>/dev/null)
  COMMITTED=$(git log -1 --format=%cI 2>/dev/null)
  FILES=$(git diff-tree --no-commit-id --name-only -r --root HEAD 2>/dev/null | tr '\n' ',' | sed 's/,$//')
  
  curl -s -X POST "{commit_endpoint}" \
    -H "Content-Type: application/json" \
    -d "{{\\"sha\\":\\"$SHA\\",\\"message\\":\\"$MSG\\",\\"committed_at\\":\\"$COMMITTED\\",\\"files\\":\\"$FILES\\"}}" >/dev/null 2>&1
) &
exit 0
HOOKEOF
    chmod +x .git/hooks/post-commit
    echo "  [OK] Installed Git post-commit hook (automatic tracking on every git commit)"
fi

# 3. Inject MCP server configuration into Windsurf
WINDSURF_CONFIG="$HOME/.codeium/windsurf/mcp_config.json"
mkdir -p "$(dirname "$WINDSURF_CONFIG")"
python3 - << 'PYEOF'
import json, os
p = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")
data = json.load(open(p)) if os.path.exists(p) else {{}}
data.setdefault("mcpServers", {{}})["learnloop"] = {{
    "serverUrl": "{base_url}/mcp"
}}
with open(p, "w") as f:
    json.dump(data, f, indent=2)
print("  [OK] Injected LearnLoop into Windsurf")

# Devin Desktop on Linux/Mac
dp = os.path.expanduser("~/.devin/mcp.json")
if os.path.exists(os.path.dirname(dp)):
    ddata = json.load(open(dp)) if os.path.exists(dp) else {{}}
    ddata.setdefault("mcpServers", {{}})["learnloop"] = {{
        "type": "streamable-http",
        "url": "{base_url}/mcp"
    }}
    with open(dp, "w") as f:
        json.dump(ddata, f, indent=2)
    print("  [OK] Injected LearnLoop into Devin Desktop")

# 4. Inject MCP into VS Code workspace if .vscode exists
if os.path.exists(".vscode"):
    vp = ".vscode/settings.json"
    try:
        vdata = json.load(open(vp)) if os.path.exists(vp) else {{}}
        vdata.setdefault("mcpServers", {{}})["learnloop"] = {{
            "type": "streamable-http",
            "url": "{base_url}/mcp"
        }}
        with open(vp, "w") as f:
            json.dump(vdata, f, indent=2)
        print("  [OK] Injected LearnLoop into VS Code (.vscode/settings.json)")
    except Exception as e:
        print(f"  [!] VS Code settings update skipped: {{e}}")
PYEOF

echo "Successfully integrated LearnLoop MCP and Rules on the fly!"
echo "Every 'git commit' will now track automatically without manual prompting!"
'''
    return script


def main():
    """Main entry point for the HTTP server."""
    parser = argparse.ArgumentParser(description="LearnLoop HTTP Server")
    parser.add_argument(
        "--host",
        default=os.getenv("LEARNLOOP_HTTP_HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("LEARNLOOP_HTTP_PORT", "8000")),
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting LearnLoop HTTP server on {args.host}:{args.port}")
    logger.info(f"Dashboard available at: http://localhost:{os.getenv('LEARNLOOP_DASHBOARD_PORT', '8765')}")
    logger.info(f"API documentation: http://{args.host}:{args.port}/docs")
    logger.info(f"MCP SSE endpoint: http://{args.host}:{args.port}/sse")
    logger.info(f"MCP JSON-RPC: http://{args.host}:{args.port}/mcp/v1/tools")
    
    target = "learnloop_http:app" if args.reload else app
    uvicorn.run(
        target,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
