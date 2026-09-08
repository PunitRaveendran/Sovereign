"""
config.py — Central configuration for Sovereign / Manoj components.
All values can be overridden via environment variables or a .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Paths ──────────────────────────────────────────────────────────────
    base_dir: Path = Field(default=Path(__file__).parent, description="Project root")
    data_dir: Path = Field(default=Path(__file__).parent / "data", description="Raw document store")
    chroma_dir: Path = Field(default=Path(__file__).parent / "chroma_db", description="Chroma persist directory")
    output_dir: Path = Field(default=Path(__file__).parent / "outputs", description="Generated deliverables")
    audit_log_path: Path = Field(default=Path(__file__).parent / "audit.log", description="RBAC audit log")

    # ── Chroma ────────────────────────────────────────────────────────────
    chroma_collection: str = "sovereign_kb"

    # ── Embedding model ───────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cpu"          # or "cuda" if available

    # ── Chunking ──────────────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64

    # ── RAG retrieval ─────────────────────────────────────────────────────
    retrieval_k: int = 6

    # ── Network monitor ───────────────────────────────────────────────────
    monitor_interface: str = "Ethernet"    # change per machine; "lo" on Linux demo
    monitor_poll_interval: float = 1.0    # seconds

    # ── API ────────────────────────────────────────────────────────────────
    api_host: str = "127.0.0.1"
    api_port: int = 8001


settings = Settings()

# Ensure directories exist at import time
for _dir in (settings.data_dir, settings.chroma_dir, settings.output_dir):
    _dir.mkdir(parents=True, exist_ok=True)
