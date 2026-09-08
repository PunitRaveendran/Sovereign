import os
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.router import TaskRouter
from app.core.agent import SovereignAgent
from app.core.vram import VRAMMonitor
from app.core.audit import AuditLogger
from app.multimodal.pipeline import MultimodalPipeline

app = FastAPI(title="Sovereign AI Workbench", version="0.1.0")

# ── Gap 0 Fix: CORS for dev mode (frontend on :5500, backend on :8000) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Gap 5 Fix: Frontend→Backend role name mapping ──
FRONTEND_TO_BACKEND_ROLE = {
    "web_dev": "Engineer",
    "department_lead": "Department Manager",
    "management": "Plant Head",
    "vp_ceo": "Executive",
}

def resolve_role(frontend_role: str) -> str:
    """Map frontend role name to backend RBAC role name."""
    return FRONTEND_TO_BACKEND_ROLE.get(frontend_role, frontend_role)

class TaskRequest(BaseModel):
    user_id: str
    role: str
    task_description: str
    context_files: Optional[list[str]] = None

class TaskResponse(BaseModel):
    status: str
    routed_to_model: str
    agent_output: Dict[str, Any]
    multimodal_meta: Optional[Dict[str, Any]] = None

@app.on_event("startup")
async def startup_event():
    # Initialize components
    app.state.router = TaskRouter()
    app.state.agent = SovereignAgent()
    app.state.vram = VRAMMonitor()
    app.state.multimodal = MultimodalPipeline()
    print("Sovereign AI Gateway started. Router, Agent, VRAM Monitor, and Multimodal Pipeline initialized.")

@app.get("/health")
def health_check():
    """System health check with live GPU VRAM usage."""
    return {
        "status": "ok",
        "service": "sovereign",
        "vram": app.state.vram.get_usage()
    }

@app.get("/api/v1/vram")
def vram_telemetry():
    """Dedicated endpoint for live hardware VRAM telemetry."""
    return app.state.vram.get_usage()

@app.post("/api/v1/task", response_model=TaskResponse)
async def process_task(request: TaskRequest):
    """
    Main endpoint for incoming text-only tasks.
    """
    try:
        backend_role = resolve_role(request.role)
        model_category = app.state.router.classify(request.task_description)
        agent_result = await app.state.agent.run(request.task_description, backend_role, user_id=request.user_id)
        
        return TaskResponse(
            status="success",
            routed_to_model=model_category,
            agent_output=agent_result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/task/upload", response_model=TaskResponse)
async def process_task_with_file(
    file: UploadFile = File(...),
    user_id: str = Form("user"),
    role: str = Form("web_dev"),
    prompt: Optional[str] = Form("Inspect this equipment document/scan and formulate actionable findings.")
):
    """
    Unified multimodal upload endpoint.
    Extracts text/visual features via OCR/Vision, then passes it directly into
    the LangGraph agent cycle, strictly enforcing RBAC gatekeeping and cryptographic audit logging.
    """
    suffix = Path(file.filename or "").suffix.lower()
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".txt"}
    
    if suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {list(allowed_suffixes)}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    try:
        # Step 1: Multimodal OCR / Vision feature extraction
        multimodal_res = app.state.multimodal.process(temp_path, prompt=prompt)
        extracted_text = multimodal_res.get("extracted_text", "")

        # Step 2: Feed into the exact same LangGraph agent, RBAC gate, and Audit ledger
        grounded_task = (
            f"{prompt}\n\n"
            f"[Uploaded Deliverable: {file.filename} via {multimodal_res.get('processor')}]\n"
            f"{extracted_text}"
        )

        backend_role = resolve_role(role)
        model_category = app.state.router.classify(grounded_task)
        agent_result = await app.state.agent.run(grounded_task, backend_role, user_id=user_id)

        return TaskResponse(
            status="success",
            routed_to_model=model_category,
            agent_output=agent_result,
            multimodal_meta={
                "file": file.filename,
                "processor": multimodal_res.get("processor"),
                "type": multimodal_res.get("type")
            }
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)

# ── Gap 4 Fix: GET /api/v1/audit — serve audit log entries ──
@app.get("/api/v1/audit")
def get_audit_log(limit: int = 50):
    """Return the last N entries from the audit log."""
    log_path = os.path.join(os.getcwd(), "audit_log.jsonl")
    if not os.path.exists(log_path):
        return []
    entries = []
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    # Return the most recent entries (last N)
    return entries[-limit:]

# ── Gap 6 Fix: GET /api/v1/download/{filename} — serve generated files ──
@app.get("/api/v1/download/{filename}")
async def download_file(filename: str):
    """Serve a generated deliverable file for download."""
    clean_filename = os.path.basename(filename)
    search_paths = [
        os.path.join(os.getcwd(), "manoj", "outputs"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "manoj", "outputs"),
        os.path.join(os.getcwd(), "manoj", "generated_docs"),
        os.path.join(os.getcwd(), "manoj"),
        os.getcwd(),
    ]
    for base in search_paths:
        file_path = os.path.join(base, clean_filename)
        if os.path.isfile(file_path):
            return FileResponse(
                path=file_path,
                filename=clean_filename,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document" if clean_filename.endswith(".docx") else "application/octet-stream",
            )
    raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

# ── Serve sovereign-frontend as static files at root ──
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sovereign-frontend")
if os.path.isdir(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
