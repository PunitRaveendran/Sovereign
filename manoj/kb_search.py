"""
kb_search.py — Knowledge-base search tool for the Sovereign agent.

This is the tool the agent core (Punit) calls for RAG retrieval.
RBAC is enforced HERE, at retrieval time, as a hard Chroma metadata filter.
The model never sees chunks it is not permitted to access.

Interface:
    search_kb(query, user, role, k=6) -> KBSearchResult

The function is also exposed as a FastAPI endpoint at POST /kb/search
so the agent can call it over the local loopback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chromadb import PersistentClient
from chromadb.utils import embedding_functions
from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel

from config import settings
from rbac import AccessLevel, Role, RBACGate, AuditLogger, build_rbac

# ── Singleton instances ────────────────────────────────────────────────────────

_rbac_gate: RBACGate | None = None
_audit: AuditLogger | None = None
_collection = None


def _get_rbac() -> tuple[RBACGate, AuditLogger]:
    global _rbac_gate, _audit
    if _rbac_gate is None:
        _rbac_gate, _audit = build_rbac(settings.audit_log_path)
    return _rbac_gate, _audit


def _get_collection():
    global _collection
    if _collection is None:
        client = PersistentClient(path=str(settings.chroma_dir))
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model,
            device=settings.embedding_device,
        )
        _collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class KBChunk:
    text: str
    source: str
    filename: str
    access_level: str
    chunk_index: int
    distance: float
    extra_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KBSearchResult:
    query: str
    user: str
    role: str
    chunks: list[KBChunk]
    denied: bool = False
    denial_reason: str = ""

    def as_context_string(self) -> str:
        """Format chunks as a clean context block for the LLM prompt."""
        if self.denied or not self.chunks:
            return ""
        parts = []
        for i, c in enumerate(self.chunks, 1):
            parts.append(
                f"[Source {i}: {c.filename} (access={c.access_level})]\n{c.text}"
            )
        return "\n\n---\n\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "user": self.user,
            "role": self.role,
            "denied": self.denied,
            "denial_reason": self.denial_reason,
            "chunks": [
                {
                    "text": c.text,
                    "source": c.source,
                    "filename": c.filename,
                    "access_level": c.access_level,
                    "chunk_index": c.chunk_index,
                    "distance": c.distance,
                }
                for c in self.chunks
            ],
        }


# ── Core search function ───────────────────────────────────────────────────────

def search_kb(
    query: str,
    user: str,
    role: Role,
    k: int | None = None,
    *,
    min_score: float = 0.85,   # Chroma cosine distance threshold (lower = more similar)
) -> KBSearchResult:
    """
    Retrieve top-k chunks from the KB that match *query*, filtered to
    only the access levels permitted for *role*.

    Args:
        query:      Natural-language search query from the agent.
        user:       Username (for audit logging).
        role:       Role enum — determines which access levels are visible.
        k:          Number of results to return (default from settings).
        min_score:  Maximum cosine distance to include (filters noise).

    Returns:
        KBSearchResult with chunks or denial info.
    """
    gate, audit = _get_rbac()
    collection = _get_collection()
    k = k or settings.retrieval_k

    # Build the hard metadata filter — this is the actual security boundary
    where_filter = gate.chroma_filter(role)
    logger.info(
        "KB search | user={} role={} filter={} k={} query={}",
        user, role, where_filter, k, query[:80],
    )

    # Log access attempt (resource = "kb_search")
    audit.log_access(
        user=user,
        role=role,
        resource="kb_search",
        requested_level=AccessLevel.PUBLIC,  # retrieval itself is public; filter handles the rest
        granted=True,
        reason=f"filter={where_filter}",
    )

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(k, collection.count() or 1),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.error("Chroma query failed: {}", exc)
        return KBSearchResult(
            query=query, user=user, role=role.value,
            chunks=[], denied=True, denial_reason=str(exc),
        )

    docs      = (results.get("documents")  or [[]])[0]
    metas     = (results.get("metadatas")  or [[]])[0]
    distances = (results.get("distances")  or [[]])[0]

    chunks: list[KBChunk] = []
    for doc, meta, dist in zip(docs, metas, distances):
        if dist > min_score:
            continue  # below relevance threshold
        chunks.append(
            KBChunk(
                text=doc,
                source=meta.get("source", ""),
                filename=meta.get("filename", ""),
                access_level=meta.get("access_level", ""),
                chunk_index=int(meta.get("chunk_index", 0)),
                distance=round(dist, 4),
            )
        )

    logger.info("KB search returned {} relevant chunks for user={}", len(chunks), user)
    return KBSearchResult(query=query, user=user, role=role.value, chunks=chunks)


# ── FastAPI endpoint ───────────────────────────────────────────────────────────

app = FastAPI(title="Sovereign KB Search Service", version="1.0.0")


class SearchRequest(BaseModel):
    query: str
    user: str
    role: str          # Role enum value as string
    k: int = 6
    min_score: float = 0.85


class AuditRequest(BaseModel):
    n: int = 50


@app.post("/kb/search")
async def api_search(req: SearchRequest):
    try:
        role = Role(req.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown role: '{req.role}'")

    result = search_kb(
        query=req.query,
        user=req.user,
        role=role,
        k=req.k,
        min_score=req.min_score,
    )
    return result.to_dict()


@app.get("/kb/health")
async def health():
    collection = _get_collection()
    return {"status": "ok", "doc_count": collection.count()}


@app.post("/kb/audit")
async def api_audit(req: AuditRequest):
    _, audit = _get_rbac()
    return {"records": audit.read_recent(req.n)}


@app.get("/kb/audit")
async def api_audit_get(n: int = 50):
    _, audit = _get_rbac()
    return {"records": audit.read_recent(n)}


# ── Standalone run ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "kb_search:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level="info",
    )
