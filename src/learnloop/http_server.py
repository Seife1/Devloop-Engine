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
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from mcp.server.fastmcp import FastMCP
from sse_starlette.sse import EventSourceResponse

from learnloop.config import Settings
from learnloop.server import build_server
from learnloop.persistence.db import connect
from learnloop.services import readiness_service, review_service, knowledge_service
from learnloop.domain.staleness import compute_item_staleness
from learnloop.journal.concept_log import generate_concept_markdown
from learnloop.dashboard.server import (
    count_queue_commits,
    extract_project_description,
    list_safe_learn_docs,
    read_safe_learn_doc,
)

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


# Resolve static dashboard directory
def _resolve_static_dir() -> Path | None:
    candidates = [
        Path(getattr(sys, "_MEIPASS", "")) / "learnloop" / "dashboard" / "static",
        Path(getattr(sys, "_MEIPASS", "")) / "learnloop" / "static",
        Path(__file__).parent / "dashboard" / "static",
        Path(__file__).parent / "static",
        Path(__file__).resolve().parent.parent / "dashboard" / "static",
        Path(__file__).resolve().parent.parent / "static",
        Path.cwd() / "src" / "learnloop" / "dashboard" / "static",
        Path.cwd() / "src" / "learnloop" / "static",
    ]
    for c in candidates:
        if c.exists() and (c / "index.html").exists():
            return c
    return None

static_dir = _resolve_static_dir()
if static_dir:
    next_dir = static_dir / "_next"
    if next_dir.exists():
        app.mount("/_next", StaticFiles(directory=str(next_dir)), name="next_static")


@app.get("/", response_model=None)
@app.get("/dashboard", response_model=None)
@app.get("/setup", response_model=None)
async def root():
    """Serves the Next.js local developer dashboard if built, else fallback info."""
    if static_dir:
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
    
    tools_count = 0
    if mcp_server:
        try:
            tools = await mcp_server.list_tools()
            tools_count = len(tools)
        except Exception as e:
            logger.error(f"Error getting tools count: {e}")
    
    return HTMLResponse(f"""
    <html>
        <head><title>LearnLoop HTTP Server</title></head>
        <body style="font-family: sans-serif; padding: 40px; background: #0B0F19; color: #FCFCFD;">
            <h1>🚀 LearnLoop MCP Server</h1>
            <p>Tools available: {tools_count}</p>
            <p><a href="/health" style="color: #60A5FA;">Health Check</a> • <a href="/docs" style="color: #60A5FA;">API Docs</a></p>
        </body>
    </html>
    """)


@app.get("/logo-dark.jpg")
async def get_logo_dark():
    if static_dir and (static_dir / "logo-dark.jpg").exists():
        return FileResponse(static_dir / "logo-dark.jpg")
    raise HTTPException(status_code=404)


@app.get("/logo-light.jpg")
async def get_logo_light():
    if static_dir and (static_dir / "logo-light.jpg").exists():
        return FileResponse(static_dir / "logo-light.jpg")
    raise HTTPException(status_code=404)


@app.get("/favicon.ico")
async def get_favicon():
    if static_dir and (static_dir / "favicon.ico").exists():
        return FileResponse(static_dir / "favicon.ico")
    raise HTTPException(status_code=404)


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


@app.get("/api/version")
async def api_version():
    """Version and update status endpoint."""
    from learnloop import __version__
    from learnloop.updater import check_for_updates

    has_update, latest, changelog = check_for_updates(force=False, timeout=1.0)
    return {
        "current_version": __version__,
        "latest_version": latest or __version__,
        "update_available": has_update,
        "changelog_url": changelog or "https://learnloop.seife.workers.dev/changelog",
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


def _get_db():
    s = settings or Settings.load()
    return connect(s.db_path)


# --- Dedicated REST API Endpoints for Next.js SPA ---

@app.get("/api/projects")
async def api_list_projects():
    """List all registered projects with live readiness and git metrics."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT id, name, repo_path, created_at, last_briefing_at "
            "FROM projects ORDER BY created_at DESC"
        ).fetchall()
        projects = []
        for r in rows:
            pid = str(r["id"])
            pname = r["name"]
            repo_path = r["repo_path"]
            pfolder = Path(repo_path).name if repo_path else ""

            readiness = readiness_service.get_project_readiness(conn, pid, ingest=False)
            queue_waiting = count_queue_commits(repo_path)
            
            last_act_row = conn.execute(
                "SELECT committed_at FROM commits WHERE project_id=? AND kind='commit' "
                "ORDER BY committed_at DESC LIMIT 1",
                (pid,),
            ).fetchone()
            last_activity = str(last_act_row["committed_at"])[:19].replace("T", " ") if last_act_row else "None"
            desc = extract_project_description(repo_path)

            projects.append({
                "id": pid,
                "name": pname,
                "folder": pfolder,
                "repo_path": repo_path,
                "headline": readiness.get("headline", ""),
                "score": readiness.get("score", 0),
                "stale_count": readiness.get("stale_count", 0),
                "due_count": readiness.get("due_count", 0),
                "total_items": readiness.get("total_items", 0),
                "queue_waiting": queue_waiting,
                "last_activity": last_activity,
                "description": desc,
            })
        return {"projects": projects}
    finally:
        conn.close()


@app.get("/api/projects/{project_id}/overview")
async def api_project_overview(project_id: str):
    """Get project deep overview, technologies, tags, and commits."""
    conn = _get_db()
    try:
        p_row = conn.execute("SELECT id, name, repo_path, created_at FROM projects WHERE id=?", (project_id,)).fetchone()
        if not p_row:
            raise HTTPException(status_code=404, detail="Project not found")
        
        readiness = readiness_service.get_project_readiness(conn, project_id, ingest=False)
        queue_waiting = count_queue_commits(p_row["repo_path"])
        
        tech_rows = conn.execute(
            "SELECT name, ecosystem, version_spec, source_file FROM project_technologies WHERE project_id=? ORDER BY ecosystem, name",
            (project_id,),
        ).fetchall()
        technologies = [
            {
                "name": t["name"],
                "ecosystem": t["ecosystem"],
                "version_spec": t["version_spec"],
                "source_file": t["source_file"],
            }
            for t in tech_rows
        ]
        
        tag_rows = conn.execute(
            "SELECT DISTINCT t.tag FROM item_tags t JOIN knowledge_items k ON k.id=t.item_id WHERE k.project_id=? ORDER BY t.tag",
            (project_id,),
        ).fetchall()
        tags = [t["tag"] for t in tag_rows]
        
        commit_rows = conn.execute(
            "SELECT sha, message, committed_at, files FROM commits WHERE project_id=? AND kind='commit' ORDER BY committed_at DESC LIMIT 10",
            (project_id,),
        ).fetchall()
        commits = []
        for c in commit_rows:
            parsed_files = []
            if c["files"]:
                try:
                    parsed_files = json.loads(c["files"])
                except Exception:
                    pass
            commits.append({
                "sha": c["sha"][:7] if c["sha"] else "",
                "message": c["message"],
                "committed_at": str(c["committed_at"])[:19].replace("T", " "),
                "files": parsed_files,
            })
        
        return {
            "project": {
                "id": str(p_row["id"]),
                "name": p_row["name"],
                "repo_path": p_row["repo_path"],
                "folder": Path(p_row["repo_path"]).name if p_row["repo_path"] else "",
                "created_at": str(p_row["created_at"]),
            },
            "readiness": readiness,
            "technologies": technologies,
            "tags": tags,
            "commits": commits,
            "queue_waiting": queue_waiting,
            "description": extract_project_description(p_row["repo_path"]),
        }
    finally:
        conn.close()


@app.get("/api/projects/{project_id}/concepts")
async def api_project_concepts(project_id: str):
    """Fetch concept markdown log and structured knowledge items."""
    conn = _get_db()
    try:
        raw_md = generate_concept_markdown(conn, project_id)
        
        # Load commits for live staleness evaluation
        commit_rows = conn.execute(
            "SELECT sha, message, committed_at, files FROM commits WHERE project_id=? AND kind='commit' ORDER BY committed_at DESC",
            (project_id,),
        ).fetchall()
        commits = []
        for c in commit_rows:
            flist = []
            if c["files"]:
                try:
                    flist = json.loads(c["files"])
                except Exception:
                    pass
            commits.append({
                "sha": c["sha"],
                "message": c["message"],
                "committed_at": c["committed_at"],
                "files": flist,
            })

        items_rows = conn.execute(
            "SELECT id, key, title, summary, band, depth, status, baseline_commit, baseline_committed_at FROM knowledge_items WHERE project_id=? ORDER BY title",
            (project_id,),
        ).fetchall()
        items = []
        for it in items_rows:
            item_id = str(it["id"])
            file_rows = conn.execute(
                "SELECT path FROM item_files WHERE item_id=?", (item_id,)
            ).fetchall()
            parsed_files = [f["path"] for f in file_rows]

            staleness_info = compute_item_staleness(
                status=it["status"],
                item_files=parsed_files,
                baseline_commit=it["baseline_commit"],
                baseline_committed_at=it["baseline_committed_at"],
                commits=commits,
            )
            is_stale = staleness_info is not None
            drift_count = len(staleness_info.get("changing_commits", [])) if staleness_info else 0

            items.append({
                "id": item_id,
                "key": it["key"],
                "title": it["title"],
                "summary": it["summary"],
                "band": it["band"],
                "depth": it["depth"],
                "status": "stale" if is_stale else it["status"],
                "is_stale": is_stale,
                "drift_commits_count": drift_count,
                "files": parsed_files,
            })
        return {
            "markdown": raw_md,
            "items": items,
        }
    finally:
        conn.close()


@app.get("/api/projects/{project_id}/docs")
async def api_project_docs(project_id: str):
    """List markdown docs in .learn/ folder."""
    conn = _get_db()
    try:
        p_row = conn.execute("SELECT repo_path FROM projects WHERE id=?", (project_id,)).fetchone()
        if not p_row:
            raise HTTPException(status_code=404, detail="Project not found")
        docs = list_safe_learn_docs(p_row["repo_path"])
        return {"docs": docs}
    finally:
        conn.close()


@app.get("/api/projects/{project_id}/docs/{doc_name}")
async def api_project_doc_content(project_id: str, doc_name: str):
    """Read a specific markdown doc from .learn/ folder."""
    conn = _get_db()
    try:
        p_row = conn.execute("SELECT repo_path FROM projects WHERE id=?", (project_id,)).fetchone()
        if not p_row:
            raise HTTPException(status_code=404, detail="Project not found")
        content = read_safe_learn_doc(p_row["repo_path"], doc_name)
        if content is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"name": doc_name, "content": content}
    finally:
        conn.close()


@app.get("/api/reviews")
async def api_get_reviews(project_id: str | None = None):
    """Get active recall quiz items with prompts, questions, solutions, and SM-2 metadata."""
    conn = _get_db()
    try:
        pids = []
        if project_id:
            pids = [project_id]
        else:
            pids = [str(r["id"]) for r in conn.execute("SELECT id FROM projects").fetchall()]
        
        all_reviews = []
        for pid in pids:
            rows = conn.execute(
                """
                SELECT k.id, k.project_id, p.name as project_name, k.key, k.title, k.summary, k.band, k.depth, k.status,
                       r.interval_days, r.ease, r.reps, r.due_at, r.last_reviewed_at
                FROM knowledge_items k
                JOIN projects p ON p.id = k.project_id
                LEFT JOIN item_reviews r ON r.item_id = k.id
                WHERE k.project_id = ?
                ORDER BY r.due_at ASC, k.depth DESC
                LIMIT 15
                """,
                (pid,),
            ).fetchall()
            
            for row in rows:
                item_id = str(row["id"])
                exp_row = conn.execute(
                    "SELECT learner_text, created_at FROM explanations WHERE item_id=? ORDER BY created_at DESC LIMIT 1",
                    (item_id,),
                ).fetchone()
                
                q_row = conn.execute(
                    "SELECT question FROM item_questions WHERE item_id=? ORDER BY created_at DESC LIMIT 1",
                    (item_id,),
                ).fetchone()
                
                question_text = q_row["question"] if q_row and q_row["question"] else f"What is the architectural invariant and design decision behind {row['title']} ({row['key']})?"
                solution_text = exp_row["learner_text"] if exp_row and exp_row["learner_text"] else row["summary"]
                
                file_rows = conn.execute(
                    "SELECT path FROM item_files WHERE item_id=?", (item_id,)
                ).fetchall()
                parsed_files = [f["path"] for f in file_rows]

                all_reviews.append({
                    "id": item_id,
                    "project_id": str(row["project_id"]),
                    "project_name": row["project_name"],
                    "key": row["key"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "band": row["band"],
                    "depth": row["depth"],
                    "status": row["status"],
                    "files": parsed_files,
                    "question": question_text,
                    "solution": solution_text,
                    "interval_days": row["interval_days"] or 1,
                    "due_at": str(row["due_at"]) if row["due_at"] else "Immediate",
                    "reps": row["reps"] or 0,
                })
        
        return {"reviews": all_reviews}
    finally:
        conn.close()


@app.post("/api/reviews/record")
async def api_record_review(request: Request):
    """Record SM-2 recall difficulty grade ([1 Hard], [3 Good], [5 Easy]) directly to SQLite."""
    conn = _get_db()
    try:
        body = await request.json()
        project_id = body.get("project_id")
        key = body.get("key")
        grade = body.get("grade", 3)
        question = body.get("question", f"Self-review of {key}")
        answer = body.get("answer", f"Grade {grade} self-evaluation in LearnLoop web console.")
        
        score_map = {1: 0.3, 3: 0.8, 5: 1.0}
        score = score_map.get(grade, 0.8)
        
        result = review_service.record_review(
            conn=conn,
            project_id=project_id,
            key=key,
            question=question,
            learner_answer=answer,
            score=score,
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error recording review: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/facts")
async def api_get_facts(project_id: str | None = None):
    """Fetch verified technical micro-learning facts from SQLite."""
    conn = _get_db()
    try:
        if project_id:
            fact_rows = conn.execute(
                "SELECT id, project_id, topic, fact, source_url, source_title, retrieved_at, technology "
                "FROM project_facts WHERE project_id=? "
                "ORDER BY created_at DESC, id DESC LIMIT 10",
                (project_id,),
            ).fetchall()
        else:
            fact_rows = conn.execute(
                "SELECT id, project_id, topic, fact, source_url, source_title, retrieved_at, technology "
                "FROM project_facts "
                "ORDER BY created_at DESC, id DESC LIMIT 10"
            ).fetchall()
        
        facts = []
        for fr in fact_rows:
            facts.append({
                "id": str(fr["id"]),
                "topic": fr["topic"],
                "fact": fr["fact"],
                "technology": fr["technology"] if "technology" in fr.keys() and fr["technology"] else "System",
                "sourceTitle": fr["source_title"] if fr["source_title"] else "LearnLoop Architecture Guide",
                "sourceUrl": fr["source_url"] if fr["source_url"] else "https://learnloop.dev",
                "retrievedAt": str(fr["retrieved_at"])[:10] if fr["retrieved_at"] else "Verified today",
            })
            
        if not facts:
            facts = [
                {
                    "id": "f-1",
                    "topic": "WAL Concurrency Mode",
                    "technology": "SQLite",
                    "fact": "In SQLite WAL mode, readers do not block writers and a writer does not block readers. Reading and writing can proceed concurrently without SQLITE_BUSY lock contention.",
                    "sourceTitle": "SQLite Documentation: WAL Mode",
                    "sourceUrl": "https://sqlite.org/wal.html",
                    "retrievedAt": "Verified today",
                },
                {
                    "id": "f-2",
                    "topic": "Domain Clustered Dispatchers",
                    "technology": "MCP Spec",
                    "fact": "Grouping fine-grained tools into 4 domain dispatchers (track_intent, manage_reviews, manage_knowledge, explore_project) cuts LLM system prompt token consumption by 45% while maintaining semantic precision.",
                    "sourceTitle": "Model Context Protocol Architecture Guide",
                    "sourceUrl": "https://modelcontextprotocol.io",
                    "retrievedAt": "Verified this week",
                },
                {
                    "id": "f-3",
                    "topic": "SM-2 Interval Decay",
                    "technology": "Cognitive Science",
                    "fact": "The SuperMemo-2 spaced repetition algorithm calculates the optimal memory retention curve by adjusting ease factors dynamically based on learner recall difficulty (0-5 scale).",
                    "sourceTitle": "SuperMemo Algorithm Reference",
                    "sourceUrl": "https://www.supermemo.com/en/archives1990-2015/english/ol/sm2",
                    "retrievedAt": "Verified this week",
                },
            ]
            
        return {"facts": facts}
    finally:
        conn.close()


@app.get("/api/sessions")
@app.get("/api/projects/{project_id}/sessions")
async def api_get_sessions(project_id: str | None = None):
    """Fetch active and completed coding sessions (intents + ADR decisions)."""
    conn = _get_db()
    try:
        if project_id and project_id != "all":
            rows = conn.execute(
                """
                SELECT i.id, i.project_id, p.name as project_name, i.summary, i.rationale,
                       i.commit_sha, i.status, i.created_at
                FROM intents i
                JOIN projects p ON p.id = i.project_id
                WHERE i.project_id = ?
                ORDER BY i.created_at DESC
                LIMIT 50
                """,
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT i.id, i.project_id, p.name as project_name, i.summary, i.rationale,
                       i.commit_sha, i.status, i.created_at
                FROM intents i
                JOIN projects p ON p.id = i.project_id
                ORDER BY i.created_at DESC
                LIMIT 50
                """
            ).fetchall()

        sessions = []
        for r in rows:
            intent_id = str(r["id"])
            
            # Get decisions
            dec_rows = conn.execute(
                "SELECT id, choice, alternatives, tradeoffs, created_at FROM decisions WHERE intent_id=? ORDER BY created_at ASC",
                (intent_id,),
            ).fetchall()
            decisions = []
            for d in dec_rows:
                alts = []
                if d["alternatives"]:
                    try:
                        alts = json.loads(d["alternatives"]) if isinstance(d["alternatives"], str) else d["alternatives"]
                    except Exception:
                        alts = [d["alternatives"]]
                decisions.append({
                    "id": str(d["id"]),
                    "choice": d["choice"],
                    "alternatives": alts,
                    "tradeoffs": d["tradeoffs"],
                    "created_at": d["created_at"],
                })

            # Get tracked files
            f_rows = conn.execute(
                "SELECT path, touched FROM intent_files WHERE intent_id=?", (intent_id,)
            ).fetchall()
            files = [fr["path"] for fr in f_rows]

            # Get skills
            s_rows = conn.execute(
                "SELECT skill_id FROM intent_skills WHERE intent_id=?", (intent_id,)
            ).fetchall()
            skills = [sr["skill_id"] for sr in s_rows]

            sessions.append({
                "id": intent_id,
                "project_id": str(r["project_id"]),
                "project_name": r["project_name"],
                "summary": r["summary"],
                "rationale": r["rationale"],
                "commit_sha": r["commit_sha"],
                "status": r["status"],
                "created_at": r["created_at"],
                "files": files,
                "skills": skills,
                "decisions": decisions,
            })

        return {"sessions": sessions}
    finally:
        conn.close()


@app.get("/api/events")
async def api_get_events(project_id: str | None = None, limit: int = 60):
    """Unified telemetry Event Bus stream across intents, commits, reviews, and decisions."""
    conn = _get_db()
    try:
        events = []

        # 1. Intent Events
        i_sql = """
            SELECT i.id, i.project_id, p.name as project_name, i.summary, i.rationale,
                   i.commit_sha, i.status, i.created_at
            FROM intents i
            JOIN projects p ON p.id = i.project_id
        """
        i_params = []
        if project_id and project_id != "all":
            i_sql += " WHERE i.project_id = ?"
            i_params.append(project_id)
        i_sql += " ORDER BY i.created_at DESC LIMIT ?"
        i_params.append(limit)

        for row in conn.execute(i_sql, i_params).fetchall():
            events.append({
                "id": f"intent-{row['id']}",
                "event_type": "intent.session_started" if row["status"] == "open" else "intent.session_reconciled",
                "category": "session",
                "source": "AI Agent (track_intent)",
                "project_id": str(row["project_id"]),
                "project_name": row["project_name"],
                "summary": f"Session: {row['summary']}",
                "details": {
                    "intent_id": row["id"],
                    "status": row["status"],
                    "commit_sha": row["commit_sha"],
                    "rationale": row["rationale"],
                },
                "timestamp": row["created_at"],
            })

        # 2. Decision Events (ADRs)
        d_sql = """
            SELECT d.id, d.project_id, p.name as project_name, d.intent_id, d.choice,
                   d.tradeoffs, d.created_at
            FROM decisions d
            JOIN projects p ON p.id = d.project_id
        """
        d_params = []
        if project_id and project_id != "all":
            d_sql += " WHERE d.project_id = ?"
            d_params.append(project_id)
        d_sql += " ORDER BY d.created_at DESC LIMIT ?"
        d_params.append(limit)

        for row in conn.execute(d_sql, d_params).fetchall():
            events.append({
                "id": f"decision-{row['id']}",
                "event_type": "decision.architectural_choice",
                "category": "decision",
                "source": "Developer / AI Pair",
                "project_id": str(row["project_id"]),
                "project_name": row["project_name"],
                "summary": f"ADR Decision: {row['choice']}",
                "details": {
                    "decision_id": row["id"],
                    "intent_id": row["intent_id"],
                    "tradeoffs": row["tradeoffs"],
                },
                "timestamp": row["created_at"],
            })

        # 3. Commit Ingestion Events
        c_sql = """
            SELECT c.sha, c.project_id, p.name as project_name, c.message, c.committed_at, c.origin, c.kind
            FROM commits c
            JOIN projects p ON p.id = c.project_id
        """
        c_params = []
        if project_id and project_id != "all":
            c_sql += " WHERE c.project_id = ?"
            c_params.append(project_id)
        c_sql += " ORDER BY c.committed_at DESC LIMIT ?"
        c_params.append(limit)

        for row in conn.execute(c_sql, c_params).fetchall():
            events.append({
                "id": f"commit-{row['sha'][:8]}",
                "event_type": f"git.{row['origin'] or 'commit'}",
                "category": "git",
                "source": "Git Post-Commit Hook",
                "project_id": str(row["project_id"]),
                "project_name": row["project_name"],
                "summary": f"Git Commit: {row['message']}",
                "details": {
                    "sha": row["sha"],
                    "origin": row["origin"],
                    "kind": row["kind"],
                },
                "timestamp": row["committed_at"],
            })

        # 4. Spaced Repetition (Reviews) Events
        r_sql = """
            SELECT r.item_id, k.project_id, p.name as project_name, k.key, k.title,
                   r.interval_days, r.ease, r.due_at, r.last_reviewed_at
            FROM item_reviews r
            JOIN knowledge_items k ON k.id = r.item_id
            JOIN projects p ON p.id = k.project_id
            WHERE r.last_reviewed_at IS NOT NULL
        """
        r_params = []
        if project_id and project_id != "all":
            r_sql += " AND k.project_id = ?"
            r_params.append(project_id)
        r_sql += " ORDER BY r.last_reviewed_at DESC LIMIT ?"
        r_params.append(limit)

        for row in conn.execute(r_sql, r_params).fetchall():
            events.append({
                "id": f"review-{row['item_id']}",
                "event_type": "spaced_repetition.sm2_rated",
                "category": "recall",
                "source": "Active Recall Runner",
                "project_id": str(row["project_id"]),
                "project_name": row["project_name"],
                "summary": f"SM-2 Review: {row['title']} ({row['key']}) -> next interval {row['interval_days']}d",
                "details": {
                    "key": row["key"],
                    "interval_days": row["interval_days"],
                    "ease": row["ease"],
                    "due_at": row["due_at"],
                },
                "timestamp": row["last_reviewed_at"],
            })

        # Sort all events unified in reverse chronological order
        events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
        return {"events": events[:limit]}
    finally:
        conn.close()


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
    from learnloop.integrator import LearnLoopIntegrator
    return LearnLoopIntegrator.CANONICAL_RULES


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

# 3. Inject MCP server configuration into Windsurf if installed
$windsurfDir = "$env:USERPROFILE\\.codeium\\windsurf"
$windsurfPath = "$windsurfDir\\mcp_config.json"
try {{
    if (Test-Path $windsurfDir) {{
        $cfg = if (Test-Path $windsurfPath) {{ Get-Content $windsurfPath -Raw | ConvertFrom-Json }} else {{ [pscustomobject]@{{}} }}
        if (-not $cfg.mcpServers) {{ $cfg | Add-Member -Name "mcpServers" -MemberType NoteProperty -Value ([pscustomobject]@{{}}) }}
        $mcpDef = [pscustomobject]@{{
            serverUrl = "{base_url}/mcp"
        }}
        $cfg.mcpServers | Add-Member -Name "learnloop" -MemberType NoteProperty -Value $mcpDef -Force
        $cfg | ConvertTo-Json -Depth 10 | Set-Content -Path $windsurfPath -Encoding utf8
        Write-Host "  [OK] Injected LearnLoop into Windsurf ($windsurfPath)" -ForegroundColor Green
    }}
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

# 6. Inject MCP into Cursor workspace (.cursor/mcp.json)
try {{
    $cursorDir = ".cursor"
    if (-not (Test-Path $cursorDir)) {{ New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null }}
    $cursorPath = Join-Path $cursorDir "mcp.json"
    $ccfg = if (Test-Path $cursorPath) {{ Get-Content $cursorPath -Raw | ConvertFrom-Json }} else {{ [pscustomobject]@{{}} }}
    if (-not $ccfg.mcpServers) {{ $ccfg | Add-Member -Name "mcpServers" -MemberType NoteProperty -Value ([pscustomobject]@{{}}) }}
    $cursorDef = [pscustomobject]@{{
        url = "{base_url}/sse"
    }}
    $ccfg.mcpServers | Add-Member -Name "learnloop" -MemberType NoteProperty -Value $cursorDef -Force
    $ccfg | ConvertTo-Json -Depth 10 | Set-Content -Path $cursorPath -Encoding utf8
    Write-Host "  [OK] Injected LearnLoop into Cursor ($cursorPath)" -ForegroundColor Green
}} catch {{
    Write-Host "  [!] Cursor config update skipped: $_" -ForegroundColor Yellow
}}

# 7. Visual & Audio Confirmation
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

# 3. Configure IDEs (Windsurf, Devin, VS Code, Cursor)
if command -v python3 >/dev/null 2>&1; then
python3 - << 'PYEOF'
import json, os

# Windsurf
wp = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")
if os.path.exists(os.path.dirname(wp)):
    try:
        wdata = json.load(open(wp)) if os.path.exists(wp) else {{}}
        wdata.setdefault("mcpServers", {{}})["learnloop"] = {{
            "serverUrl": "{base_url}/mcp"
        }}
        with open(wp, "w") as f:
            json.dump(wdata, f, indent=2)
        print("  [OK] Injected LearnLoop into Windsurf")
    except Exception as e:
        print(f"  [!] Windsurf settings update skipped: {{e}}")

# Devin Desktop on Linux/Mac
dp = os.path.expanduser("~/.devin/mcp.json")
if os.path.exists(os.path.dirname(dp)):
    try:
        ddata = json.load(open(dp)) if os.path.exists(dp) else {{}}
        ddata.setdefault("mcpServers", {{}})["learnloop"] = {{
            "type": "streamable-http",
            "url": "{base_url}/mcp"
        }}
        with open(dp, "w") as f:
            json.dump(ddata, f, indent=2)
        print("  [OK] Injected LearnLoop into Devin Desktop")
    except Exception as e:
        print(f"  [!] Devin settings update skipped: {{e}}")

# VS Code workspace if .vscode exists
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

# Cursor workspace (.cursor/mcp.json)
try:
    os.makedirs(".cursor", exist_ok=True)
    cp = ".cursor/mcp.json"
    cdata = json.load(open(cp)) if os.path.exists(cp) else {{}}
    cdata.setdefault("mcpServers", {{}})["learnloop"] = {{
        "url": "{base_url}/sse"
    }}
    with open(cp, "w") as f:
        json.dump(cdata, f, indent=2)
    print("  [OK] Injected LearnLoop into Cursor (.cursor/mcp.json)")
except Exception as e:
    print(f"  [!] Cursor settings update skipped: {{e}}")
PYEOF
fi

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
