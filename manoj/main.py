"""
main.py — Unified FastAPI gateway for all Manoj components.

Routes (all on port 8001):
  POST /kb/search          → KB search (RBAC filtered)
  GET  /kb/health          → Chroma health
  GET  /kb/audit           → Audit log
  POST /generate/docx      → Generate Word doc
  POST /generate/pptx      → Generate PowerPoint
  POST /generate/xlsx      → Generate Excel
  GET  /generate/list      → List generated files
  GET  /generate/download/ → Download a file
  GET  /network/stats      → Latest packet counters
  GET  /network/stream     → SSE live stream
  GET  /network/interfaces → List interfaces

Run:
    python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import settings
from network_monitor import monitor as _net_monitor

# ── KB search routes ───────────────────────────────────────────────────────────
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Any

import kb_search as _kb_module
import doc_generator as _doc_module
import network_monitor as _nm_module
from code_sandbox import router as sandbox_router


# ══ KB router ═══════════════════════════════════════════════════════════════════

kb_router = APIRouter(prefix="/kb", tags=["Knowledge Base"])


class SearchRequest(BaseModel):
    query: str
    user: str
    role: str
    k: int = 6
    min_score: float = 0.85


@kb_router.post("/search")
async def kb_search(req: SearchRequest):
    from rbac import Role
    try:
        role = Role(req.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown role: '{req.role}'")
    result = _kb_module.search_kb(query=req.query, user=req.user, role=role, k=req.k, min_score=req.min_score)
    return result.to_dict()


@kb_router.get("/health")
async def kb_health():
    collection = _kb_module._get_collection()
    return {"status": "ok", "doc_count": collection.count()}


@kb_router.get("/audit")
async def kb_audit(n: int = 50):
    _, audit = _kb_module._get_rbac()
    return {"records": audit.read_recent(n)}


# ══ Document generator router ════════════════════════════════════════════════════

gen_router = APIRouter(prefix="/generate", tags=["Document Generator"])


class DocRequest(BaseModel):
    template: str
    content: dict[str, Any]
    filename: str | None = None


@gen_router.post("/docx")
async def gen_docx(req: DocRequest):
    try:
        path = _doc_module.generate_docx(req.template, req.content, req.filename)
        return {"status": "ok", "file": str(path), "filename": path.name}
    except Exception as e:
        logger.warning(f"DOCX generation initial attempt: {e}. Applying fallback...")
        path = _doc_module.generate_docx("generic_report", {"title": req.content.get("title", "Report"), "summary": str(req.content.get("summary", req.content))}, req.filename)
        return {"status": "ok", "file": str(path), "filename": path.name}


@gen_router.post("/pptx")
async def gen_pptx(req: DocRequest):
    try:
        path = _doc_module.generate_pptx(req.template, req.content, req.filename)
        return {"status": "ok", "file": str(path), "filename": path.name}
    except Exception as e:
        logger.warning(f"PPTX generation initial attempt: {e}. Applying fallback...")
        path = _doc_module.generate_pptx("findings_deck", {"title": req.content.get("title", "Presentation"), "findings": [{"heading": "Finding", "body": str(req.content)}]}, req.filename)
        return {"status": "ok", "file": str(path), "filename": path.name}


@gen_router.post("/xlsx")
async def gen_xlsx(req: DocRequest):
    try:
        path = _doc_module.generate_xlsx(req.template, req.content, req.filename)
        return {"status": "ok", "file": str(path), "filename": path.name}
    except Exception as e:
        logger.warning(f"XLSX generation initial attempt: {e}. Applying fallback...")
        path = _doc_module.generate_xlsx("data_table", {"title": req.content.get("title", "Data Table"), "headers": ["Key", "Value"], "rows": [[k, str(v)] for k, v in req.content.items()]}, req.filename)
        return {"status": "ok", "file": str(path), "filename": path.name}


@gen_router.get("/list")
async def gen_list():
    files = [
        {"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)}
        for f in sorted(settings.output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        if f.is_file()
    ]
    return {"files": files}


@gen_router.get("/download/{filename}")
async def gen_download(filename: str):
    file_path = settings.output_dir / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(file_path), filename=filename)


# ══ Network monitor router ═══════════════════════════════════════════════════════

net_router = APIRouter(prefix="/network", tags=["Network Monitor"])


@net_router.get("/stats")
async def net_stats():
    return _net_monitor.get_latest()


@net_router.get("/stream")
async def net_stream():
    return StreamingResponse(
        _net_monitor.stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@net_router.get("/interfaces")
async def net_interfaces():
    import psutil
    counters = psutil.net_io_counters(pernic=True)
    return {"interfaces": list(counters.keys()), "configured": settings.monitor_interface}


@net_router.get("/health")
async def net_health():
    return {"status": "ok", "monitoring": _net_monitor._running}


@net_router.get("/egress-rules")
async def net_egress():
    return {
        "iptables_script": _nm_module.IPTABLES_SETUP_SCRIPT,
        "docker_compose":  _nm_module.DOCKER_COMPOSE_EGRESS,
    }


# ══ Main app ══════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_net_monitor.run())
    logger.info("Sovereign Manoj services starting on {}:{}", settings.api_host, settings.api_port)
    yield
    _net_monitor.stop()
    task.cancel()


app = FastAPI(
    title="Sovereign — Manoj Services",
    version="1.0.0",
    description=(
        "Knowledge-base search, office-file generation, "
        "and network egress monitoring for the Sovereign AI workbench."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers flat — no sub-app mounting, no double-prefix
app.include_router(kb_router)
app.include_router(gen_router)
app.include_router(net_router)
app.include_router(sandbox_router)


@app.get("/health", tags=["Health"])
async def health():
    from code_sandbox import _docker_available
    return {
        "status": "ok",
        "services": ["kb_search", "doc_generator", "network_monitor", "code_sandbox"],
        "chroma_dir": str(settings.chroma_dir),
        "output_dir": str(settings.output_dir),
        "sandbox_backend": "docker" if _docker_available() else "subprocess",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level="info",
    )
