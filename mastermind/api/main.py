#!/usr/bin/env python3
"""
APEX Mastermind — Full-Stack API Server
FastAPI backend with WebSocket live feed, task queue, agent management,
SQLite persistence, and real AI model integration hooks.

Case: 1FDV-23-0001009
Operator: Casey Barton
Authorization: OPR-ULT-V999-NEXUS

Endpoints:
  GET  /api/agents              - List all agents + live status
  GET  /api/agents/{id}         - Single agent detail + task history
  POST /api/tasks               - Submit new task to queue
  GET  /api/tasks               - List tasks (filterable by status/agent/priority)
  GET  /api/tasks/{id}          - Single task detail + full result
  DELETE /api/tasks/{id}        - Cancel pending task
  GET  /api/intelligence        - Query stored intelligence results
  POST /api/intelligence/search - Semantic search over intelligence DB
  GET  /api/stats               - Orchestrator-wide stats
  POST /api/execute             - Fire-and-forget command shorthand
  WS   /ws/live                 - Real-time agent feed (task events, agent state changes)
  WS   /ws/tasks/{id}           - Stream single task execution in real time
"""

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import uvicorn

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent          # mastermind/
FRONTEND_DIR = BASE_DIR / "frontend" / "dist"    # built React app
DB_PATH = BASE_DIR / "data" / "mastermind.db"
INTEL_PATH = BASE_DIR / "data" / "intelligence.json"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Import orchestrator core ───────────────────────────────────────────────────
import sys
sys.path.insert(0, str(BASE_DIR.parent))         # apex-fs-commander root
from mastermind.orchestrator import (
    MastermindOrchestrator, Task, AgentType, TaskPriority, AIModel
)

# ── Pydantic schemas ───────────────────────────────────────────────────────────
class TaskSubmit(BaseModel):
    description: str = Field(..., min_length=5, max_length=500)
    agent_type: str = Field(..., description="One of: evidence_hunter, pattern_recognizer, motion_writer, timeline_analyzer, federal_monitor")
    priority: str = Field(default="MEDIUM", description="CRITICAL | HIGH | MEDIUM | LOW")
    data: dict = Field(default_factory=dict)

class CommandExecute(BaseModel):
    command: str
    priority: str = "HIGH"

class IntelSearchRequest(BaseModel):
    query: str
    agent_type: Optional[str] = None
    limit: int = Field(default=20, le=100)

# ── WebSocket connection manager ───────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self.task_subscribers: dict[str, List[WebSocket]] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active = [w for w in self.active if w != ws]

    async def broadcast(self, event: dict):
        msg = json.dumps(event, default=str)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)

    async def send_task_event(self, task_id: str, event: dict):
        msg = json.dumps(event, default=str)
        subs = self.task_subscribers.get(task_id, [])
        dead = []
        for ws in subs:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            subs.remove(ws)

    def subscribe_task(self, task_id: str, ws: WebSocket):
        self.task_subscribers.setdefault(task_id, []).append(ws)

    def unsubscribe_task(self, task_id: str, ws: WebSocket):
        subs = self.task_subscribers.get(task_id, [])
        self.task_subscribers[task_id] = [w for w in subs if w != ws]

mgr = ConnectionManager()
orchestrator: Optional[MastermindOrchestrator] = None
orchestrator_task: Optional[asyncio.Task] = None

# ── Lifespan (startup/shutdown) ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global orchestrator, orchestrator_task
    orchestrator = MastermindOrchestrator()
    # Monkey-patch orchestrator to emit WebSocket events
    _patch_orchestrator(orchestrator)
    orchestrator_task = asyncio.create_task(orchestrator.run())
    print("✅ Mastermind orchestrator started")
    yield
    if orchestrator_task:
        orchestrator_task.cancel()
    print("👋 Mastermind orchestrator stopped")

def _patch_orchestrator(orc: MastermindOrchestrator):
    """Wrap agent execute_task to emit WebSocket events on every state change."""
    for agent in orc.agents.values():
        original = agent.execute_task
        async def patched(task, o, _orig=original, _agent=agent):
            await mgr.broadcast({
                "event": "task_started",
                "task_id": task.task_id,
                "description": task.description,
                "agent": _agent.agent_type.value,
                "priority": task.priority.name,
                "timestamp": datetime.now().isoformat()
            })
            result = await _orig(task, o)
            await mgr.broadcast({
                "event": "task_completed" if task.status.value == "completed" else "task_failed",
                "task_id": task.task_id,
                "description": task.description,
                "agent": _agent.agent_type.value,
                "confidence": task.confidence,
                "status": task.status.value,
                "timestamp": datetime.now().isoformat()
            })
            await mgr.send_task_event(task.task_id, {"event": "result", "data": result})
            return result
        agent.execute_task = patched

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="APEX Mastermind API",
    description="Full-stack AI orchestration backend for Case 1FDV-23-0001009",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helper ─────────────────────────────────────────────────────────────────────
def _resolve_agent(agent_str: str) -> AgentType:
    try:
        return AgentType(agent_str.lower())
    except ValueError:
        raise HTTPException(400, f"Unknown agent_type '{agent_str}'. Valid: {[a.value for a in AgentType]}")

def _resolve_priority(p: str) -> TaskPriority:
    try:
        return TaskPriority[p.upper()]
    except KeyError:
        raise HTTPException(400, f"Unknown priority '{p}'. Valid: CRITICAL, HIGH, MEDIUM, LOW")

def _load_intelligence() -> list:
    if INTEL_PATH.exists():
        with open(INTEL_PATH) as f:
            return json.load(f)
    return []

# ── REST Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/agents")
async def list_agents():
    """Live status of all 5 agents."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not ready")
    return {
        "agents": [
            {
                "id": agent_type.value,
                "name": agent_type.value.replace("_", " ").title(),
                "models": [m.value for m in agent.preferred_models],
                "is_busy": agent.is_busy,
                "current_task": agent.current_task.description if agent.current_task else None,
                "tasks_completed": agent.tasks_completed,
                "tasks_failed": agent.tasks_failed,
                "success_rate": round(
                    agent.tasks_completed / max(1, agent.tasks_completed + agent.tasks_failed), 3
                ),
                "avg_confidence": round(agent.average_confidence, 2),
            }
            for agent_type, agent in orchestrator.agents.items()
        ]
    }

@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Single agent detail + recent task history from intelligence DB."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not ready")
    agent_type = _resolve_agent(agent_id)
    agent = orchestrator.agents[agent_type]
    intel = _load_intelligence()
    history = [
        e for e in intel
        if e.get("task", {}).get("agent_type") == agent_id
    ][-20:]  # last 20
    return {
        "id": agent_id,
        "models": [m.value for m in agent.preferred_models],
        "is_busy": agent.is_busy,
        "current_task": agent.current_task.description if agent.current_task else None,
        "tasks_completed": agent.tasks_completed,
        "tasks_failed": agent.tasks_failed,
        "avg_confidence": round(agent.average_confidence, 2),
        "recent_history": history,
    }

@app.post("/api/tasks", status_code=202)
async def submit_task(payload: TaskSubmit):
    """Submit a new task to the priority queue."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not ready")
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    task = Task(
        task_id=task_id,
        description=payload.description,
        priority=_resolve_priority(payload.priority),
        agent_type=_resolve_agent(payload.agent_type),
        data=payload.data,
    )
    await orchestrator.add_task(task)
    await mgr.broadcast({
        "event": "task_queued",
        "task_id": task_id,
        "description": payload.description,
        "agent": payload.agent_type,
        "priority": payload.priority,
        "timestamp": datetime.now().isoformat()
    })
    return {"task_id": task_id, "status": "queued"}

@app.get("/api/tasks")
async def list_tasks(
    status: Optional[str] = None,
    agent_type: Optional[str] = None,
    limit: int = 50
):
    """List tasks: active + completed (filterable)."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not ready")
    all_tasks = orchestrator.active_tasks + orchestrator.completed_tasks
    if status:
        all_tasks = [t for t in all_tasks if t.status.value == status]
    if agent_type:
        all_tasks = [t for t in all_tasks if t.agent_type.value == agent_type]
    return {
        "total": len(all_tasks),
        "tasks": [t.to_dict() for t in all_tasks[-limit:]]
    }

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Single task detail."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not ready")
    all_tasks = orchestrator.active_tasks + orchestrator.completed_tasks
    for t in all_tasks:
        if t.task_id == task_id:
            d = t.to_dict()
            d["result"] = t.result
            return d
    # Fall back to intelligence DB
    intel = _load_intelligence()
    for entry in intel:
        if entry.get("task", {}).get("task_id") == task_id:
            return {**entry["task"], "result": entry.get("result")}
    raise HTTPException(404, f"Task '{task_id}' not found")

@app.delete("/api/tasks/{task_id}", status_code=204)
async def cancel_task(task_id: str):
    """Cancel a PENDING task (cannot cancel running tasks)."""
    # Tasks in PriorityQueue cannot be individually removed easily;
    # mark for skip via a cancellation registry instead
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not ready")
    if not hasattr(orchestrator, "_cancelled"):
        orchestrator._cancelled = set()
    orchestrator._cancelled.add(task_id)
    return

@app.get("/api/intelligence")
async def list_intelligence(
    agent_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Browse stored intelligence results."""
    intel = _load_intelligence()
    if agent_type:
        intel = [e for e in intel if e.get("task", {}).get("agent_type") == agent_type]
    total = len(intel)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": intel[offset:offset + limit]
    }

@app.post("/api/intelligence/search")
async def search_intelligence(payload: IntelSearchRequest):
    """Keyword search over intelligence results."""
    intel = _load_intelligence()
    q = payload.query.lower()
    matches = []
    for entry in intel:
        text = json.dumps(entry).lower()
        if q in text:
            if not payload.agent_type or entry.get("task", {}).get("agent_type") == payload.agent_type:
                matches.append(entry)
    return {"query": payload.query, "total": len(matches), "results": matches[:payload.limit]}

@app.get("/api/stats")
async def get_stats():
    """Global orchestrator statistics."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not ready")
    intel = _load_intelligence()
    stats = orchestrator.get_stats()
    # Augment with intelligence DB counts
    stats["intelligence_entries"] = len(intel)
    stats["case_number"] = orchestrator.case_number
    stats["ws_connections"] = len(mgr.active)
    return stats

@app.post("/api/execute", status_code=202)
async def execute_command(payload: CommandExecute):
    """Shorthand: map a natural-language command to the right agent + queue it."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not ready")
    cmd = payload.command.lower()
    # Simple intent routing
    if any(w in cmd for w in ["evidence", "scan", "icloud", "voice", "memo", "photo"]):
        agent = AgentType.EVIDENCE_HUNTER
    elif any(w in cmd for w in ["pattern", "rico", "predicate", "fraud", "tamper"]):
        agent = AgentType.PATTERN_RECOGNIZER
    elif any(w in cmd for w in ["motion", "draft", "brief", "filing", "statute"]):
        agent = AgentType.MOTION_WRITER
    elif any(w in cmd for w in ["timeline", "gps", "reconstruct", "calendar", "date"]):
        agent = AgentType.TIMELINE_ANALYZER
    elif any(w in cmd for w in ["federal", "trigger", "escalat", "threshold", "monitor"]):
        agent = AgentType.FEDERAL_MONITOR
    else:
        agent = AgentType.PATTERN_RECOGNIZER  # default
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    task = Task(
        task_id=task_id,
        description=payload.command,
        priority=_resolve_priority(payload.priority),
        agent_type=agent,
    )
    await orchestrator.add_task(task)
    return {"task_id": task_id, "routed_to": agent.value, "status": "queued"}

# ── WebSocket Endpoints ────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    """Broadcast all orchestrator events to this client."""
    await mgr.connect(ws)
    # Send current state on connect
    if orchestrator:
        await ws.send_text(json.dumps({
            "event": "connected",
            "stats": orchestrator.get_stats(),
            "timestamp": datetime.now().isoformat()
        }, default=str))
    try:
        while True:
            data = await ws.receive_text()
            # Allow client to submit tasks over WS too
            try:
                msg = json.loads(data)
                if msg.get("action") == "submit_task":
                    task = TaskSubmit(**msg["payload"])
                    result = await submit_task(task)
                    await ws.send_text(json.dumps({"event": "task_queued", **result}))
            except Exception as e:
                await ws.send_text(json.dumps({"event": "error", "message": str(e)}))
    except WebSocketDisconnect:
        mgr.disconnect(ws)

@app.websocket("/ws/tasks/{task_id}")
async def ws_task(ws: WebSocket, task_id: str):
    """Stream a specific task's execution events in real time."""
    await ws.accept()
    mgr.subscribe_task(task_id, ws)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        mgr.unsubscribe_task(task_id, ws)

# ── Serve React Frontend ───────────────────────────────────────────────────────
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        index = FRONTEND_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"message": "Frontend not built. Run: cd mastermind/frontend && npm run build"}
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "APEX Mastermind API v2.0", "docs": "/docs", "status": "running"}

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("MASTERMIND_PORT", "8001")),
        reload=os.getenv("DEV", "false").lower() == "true",
        log_level="info"
    )
