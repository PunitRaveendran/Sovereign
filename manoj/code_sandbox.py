"""
code_sandbox.py — Sandboxed code execution tool for Sovereign.

Runs agent-generated code in an isolated environment with:
  - Docker (primary, Aparna's setup): --network none, memory + CPU limits
  - Subprocess fallback (dev/Windows machines without Docker)

The agent sends code → sandbox runs it → returns stdout/stderr/exit code.
Nothing can reach the internet from inside the sandbox.

FastAPI endpoint: POST /tools/run_code

Interface for Punit's agent:
    POST /tools/run_code
    {
        "code": "print(2 + 2)",
        "language": "python",          # only python for now
        "timeout": 30,                 # seconds
        "stdin": ""                    # optional stdin
    }

    Response:
    {
        "stdout": "4\\n",
        "stderr": "",
        "exit_code": 0,
        "runtime_sec": 0.12,
        "backend": "docker" | "subprocess",
        "timed_out": false,
        "error": null
    }
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

# ── Config ─────────────────────────────────────────────────────────────────────

DOCKER_IMAGE        = os.environ.get("SANDBOX_DOCKER_IMAGE", "sovereign-sandbox:latest") # fallback to python:3.12-slim if custom image not built
DEFAULT_TIMEOUT     = 30                   # seconds
MAX_TIMEOUT         = 120
MAX_OUTPUT_BYTES    = 64 * 1024            # 64 KB cap — prevents runaway prints
MEMORY_LIMIT        = "1024m"              # Upgraded from 256m to 1GB to prevent numpy/scipy OOM on matrix calcs
CPU_LIMIT           = "1.0"                # Docker CPU limit (1 core)
SANDBOX_WORK_DIR    = Path(tempfile.gettempdir()) / "sovereign_sandbox"

SANDBOX_WORK_DIR.mkdir(parents=True, exist_ok=True)

# ── Models ─────────────────────────────────────────────────────────────────────

class CodeRequest(BaseModel):
    code:     str             = Field(...,   description="Python code to execute")
    language: Literal["python"] = Field("python", description="Language (python only for now)")
    timeout:  int             = Field(DEFAULT_TIMEOUT, ge=1, le=MAX_TIMEOUT)
    stdin:    str             = Field("",   description="Optional stdin input")


class CodeResult(BaseModel):
    stdout:      str
    stderr:      str
    exit_code:   int
    runtime_sec: float
    backend:     str           # "docker" or "subprocess"
    timed_out:   bool
    error:       str | None


# ── Backend detection ──────────────────────────────────────────────────────────

def _docker_available() -> bool:
    """Check if Docker daemon is running and accessible."""
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _get_active_docker_image() -> str:
    """Return sovereign-sandbox:latest if present, else fallback to python:3.12-slim."""
    for img in [DOCKER_IMAGE, "python:3.12-slim"]:
        try:
            res = subprocess.run(["docker", "image", "inspect", img], capture_output=True, timeout=3)
            if res.returncode == 0:
                return img
        except Exception:
            pass
    return "python:3.12-slim"

def _docker_image_exists() -> bool:
    """Check if any supported sandbox image is available."""
    try:
        active = _get_active_docker_image()
        result = subprocess.run(
            ["docker", "image", "inspect", active],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# ── Docker backend ─────────────────────────────────────────────────────────────

def _run_in_docker(code: str, timeout: int, stdin: str) -> CodeResult:
    """
    Execute code inside a Docker container with:
      --network none   → no internet access (Aparna's core requirement)
      --memory 256m    → prevents memory bombs
      --cpus 1.0       → prevents CPU hogging
      --rm             → auto-cleanup after run

    The code is written to a temp file and bind-mounted read-only.
    The container has no write access outside /tmp inside the container.
    """
    # Write code to a temp file on the host
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", dir=SANDBOX_WORK_DIR,
        delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        code_path = Path(f.name)

    try:
        cmd = [
            "docker", "run",
            "--rm",                             # remove container after exit
            "--network", "none",                # ← the key isolation
            "--memory", MEMORY_LIMIT,
            "--cpus", CPU_LIMIT,
            "--read-only",                      # container filesystem read-only
            "--tmpfs", "/tmp:size=64m",         # writable /tmp inside container
            "-v", f"{code_path}:/code/script.py:ro",  # code is read-only
            "-w", "/code",
            _get_active_docker_image(),
            "python", "-u", "/code/script.py",
        ]

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin.encode() if stdin else None,
                capture_output=True,
                timeout=timeout,
            )
            elapsed = time.monotonic() - start
            timed_out = False
        except subprocess.TimeoutExpired:
            elapsed = timeout
            timed_out = True
            # Kill the container by name isn't easy here since we used --rm
            return CodeResult(
                stdout="", stderr="", exit_code=-1,
                runtime_sec=round(elapsed, 3),
                backend="docker", timed_out=True,
                error=f"Execution timed out after {timeout}s",
            )

        stdout = _truncate(proc.stdout.decode("utf-8", errors="replace"))
        stderr = _truncate(proc.stderr.decode("utf-8", errors="replace"))

        logger.info(
            "Docker sandbox: exit={} runtime={:.2f}s stdout_len={} stderr_len={}",
            proc.returncode, elapsed, len(stdout), len(stderr)
        )

        return CodeResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode,
            runtime_sec=round(elapsed, 3),
            backend="docker",
            timed_out=timed_out,
            error=None,
        )

    except Exception as exc:
        logger.error("Docker sandbox error: {}", exc)
        return CodeResult(
            stdout="", stderr="", exit_code=-1,
            runtime_sec=0.0, backend="docker",
            timed_out=False, error=str(exc),
        )
    finally:
        code_path.unlink(missing_ok=True)


# ── Subprocess fallback ────────────────────────────────────────────────────────

def _run_in_subprocess(code: str, timeout: int, stdin: str) -> CodeResult:
    """
    Fallback when Docker is unavailable (Windows dev machines).
    Runs code in a subprocess with timeout — less isolated than Docker
    but good enough for dev/testing.

    Security note: this does NOT enforce --network none.
    On the actual demo machines, Docker is used.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", dir=SANDBOX_WORK_DIR,
        delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        code_path = Path(f.name)

    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }

    try:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                [sys.executable, str(code_path)],
                input=stdin.encode() if stdin else None,
                capture_output=True,
                timeout=timeout,
                env=env,
            )
            elapsed = time.monotonic() - start
            timed_out = False
        except subprocess.TimeoutExpired:
            elapsed = timeout
            timed_out = True
            return CodeResult(
                stdout="", stderr="", exit_code=-1,
                runtime_sec=round(elapsed, 3),
                backend="subprocess", timed_out=True,
                error=f"Execution timed out after {timeout}s",
            )

        stdout = _truncate(proc.stdout.decode("utf-8", errors="replace"))
        stderr = _truncate(proc.stderr.decode("utf-8", errors="replace"))

        logger.info(
            "Subprocess sandbox: exit={} runtime={:.2f}s",
            proc.returncode, elapsed,
        )

        return CodeResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode,
            runtime_sec=round(elapsed, 3),
            backend="subprocess",
            timed_out=timed_out,
            error=None,
        )

    except Exception as exc:
        logger.error("Subprocess sandbox error: {}", exc)
        return CodeResult(
            stdout="", stderr="", exit_code=-1,
            runtime_sec=0.0, backend="subprocess",
            timed_out=False, error=str(exc),
        )
    finally:
        code_path.unlink(missing_ok=True)


# ── Core function ──────────────────────────────────────────────────────────────

def run_code(req: CodeRequest) -> CodeResult:
    """
    Main entry point — auto-selects Docker or subprocess backend.
    Called by the FastAPI router and can also be imported directly by the agent.
    """
    logger.info(
        "Sandbox request: language={} timeout={} code_len={}",
        req.language, req.timeout, len(req.code)
    )

    if _docker_available():
        logger.info("Backend: Docker (--network none)")
        if not _docker_image_exists():
            logger.info("Pulling Docker image {}...", DOCKER_IMAGE)
            subprocess.run(["docker", "pull", DOCKER_IMAGE], check=True)
        return _run_in_docker(req.code, req.timeout, req.stdin)
    else:
        logger.warning(
            "Docker not available — falling back to subprocess. "
            "Network isolation NOT enforced on this machine. "
            "Use Docker on the demo machine."
        )
        return _run_in_subprocess(req.code, req.timeout, req.stdin)


# ── Utilities ──────────────────────────────────────────────────────────────────

def _truncate(text: str) -> str:
    """Cap output to MAX_OUTPUT_BYTES to prevent runaway prints flooding the API."""
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_OUTPUT_BYTES:
        truncated = encoded[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
        return truncated + f"\n... [output truncated at {MAX_OUTPUT_BYTES // 1024} KB]"
    return text


# ── FastAPI router ─────────────────────────────────────────────────────────────

router = APIRouter(prefix="/tools", tags=["Code Sandbox"])


@router.post("/run_code")
async def api_run_code(req: CodeRequest) -> CodeResult:
    """
    Execute Python code in a sandboxed environment.

    - **Docker** (primary on demo machines): `--network none`, memory + CPU limits
    - **Subprocess** (fallback on dev machines without Docker)

    The agent submits code → sandbox runs it → returns stdout/stderr/exit_code.
    """
    return run_code(req)


@router.get("/sandbox_info")
async def api_sandbox_info():
    """Return which backend is active on this machine."""
    docker_ok    = _docker_available()
    image_exists = _docker_image_exists() if docker_ok else False
    return {
        "docker_available":   docker_ok,
        "docker_image":       DOCKER_IMAGE,
        "docker_image_ready": image_exists,
        "active_backend":     "docker" if docker_ok else "subprocess",
        "network_isolated":   docker_ok,
        "memory_limit":       MEMORY_LIMIT if docker_ok else "none",
        "note": (
            "Docker is active — network isolation enforced (--network none)"
            if docker_ok else
            "Docker not available — subprocess fallback active. "
            "Install Docker on the demo machine for full isolation."
        ),
    }


@router.get("/sandbox_health")
async def api_sandbox_health():
    """Quick smoke-test: run 1+1 and verify output."""
    result = run_code(CodeRequest(code="print(1 + 1)", timeout=10))
    ok = result.stdout.strip() == "2" and result.exit_code == 0
    return {
        "status":  "ok" if ok else "error",
        "backend": result.backend,
        "output":  result.stdout.strip(),
        "error":   result.error,
    }
