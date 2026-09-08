"""FastAPI entry point for Sovereign."""

from pathlib import Path
import shutil
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

from backend.app.services.task_service import TaskService


app = FastAPI(
    title="Sovereign AI Workbench",
    description="Air-gapped AI workbench for confidential industrial work",
    version="0.1.0",
)


class TaskRequest(BaseModel):
    """Request body for a text-only Sovereign task."""

    prompt: str


@app.get("/health")
def health_check():
    """Verify that the Sovereign backend is running."""
    return {
        "status": "ok",
        "service": "sovereign",
    }


def get_task_service() -> TaskService:
    """Create the default TaskService."""
    return TaskService()


@app.post("/task")
def execute_task(request: TaskRequest):
    """Execute a text-only user task."""
    service = get_task_service()

    result = service.execute(
        prompt=request.prompt,
    )

    return result


@app.post("/task/upload")
def execute_task_with_file(
    prompt: str = Form(...),
    file: UploadFile = File(...),
):
    """Execute a task with an uploaded image or PDF."""

    service = get_task_service()

    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".pdf"}:
        return {
            "error": f"Unsupported file type: {suffix}"
        }

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp_file:

        shutil.copyfileobj(file.file, temp_file)

        temp_path = temp_file.name

    try:
        result = service.execute(
            prompt=prompt,
            file_path=temp_path,
        )

        return result

    finally:
        Path(temp_path).unlink(missing_ok=True)