"""
ingestor.py — Chroma ingestion pipeline for Sovereign.

Responsibilities:
  1. Accept a file (PDF, DOCX, TXT, image) or a directory of files.
  2. Extract raw text (PyMuPDF for PDFs, python-docx for Word, OCR for images).
  3. Chunk text with overlap using LangChain's RecursiveCharacterTextSplitter.
  4. Tag every chunk with RBAC metadata (access_level) at ingestion time.
  5. Embed with bge-small-en-v1.5 and upsert into Chroma.
  6. Log progress with rich + loguru.

Usage (CLI):
    python ingestor.py --path ./data --access-level public
    python ingestor.py --path ./data/exec_report.pdf --access-level executive
    python ingestor.py --list            # show all ingested documents

Architecture note:
  Access levels are assigned HERE at ingestion — not at query time.
  This is the core of the RBAC design: the metadata is baked into every
  Chroma chunk so retrieval filters are enforced on hard metadata, not soft
  model instructions.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterator

import fitz  # PyMuPDF
import typer
from chromadb import PersistentClient
from chromadb.utils import embedding_functions
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from PIL import Image
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.table import Table

# Local imports
from config import settings
from rbac import AccessLevel

# ── Globals ───────────────────────────────────────────────────────────────────

console = Console()
app = typer.Typer(help="Sovereign KB ingestor — chunk, embed, tag, and store documents.")


# ── Embedding function (Chroma-native, no extra server needed) ────────────────

def get_embedding_fn():
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
    )


# ── Chroma client ─────────────────────────────────────────────────────────────

def get_collection():
    client = PersistentClient(path=str(settings.chroma_dir))
    ef = get_embedding_fn()
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_pdf(path: Path) -> str:
    """Extract text from PDF; falls back to OCR if page has no text layer."""
    doc = fitz.open(str(path))
    pages: list[str] = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()
        if len(text) < 50:
            # Likely scanned page — render and OCR
            logger.info("Page {} of {} appears scanned, running OCR…", page_num + 1, path.name)
            text = _ocr_page(page, path.name, page_num)
        pages.append(text)
    return "\n\n".join(pages)


def _ocr_page(page: fitz.Page, fname: str, page_num: int) -> str:
    """Render a PDF page to image and OCR it with Tesseract."""
    try:
        import pytesseract
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img, lang="eng")
        logger.debug("OCR completed for {} page {}", fname, page_num + 1)
        return text
    except ImportError:
        logger.warning("pytesseract not installed; skipping OCR for page {}", page_num + 1)
        return ""
    except Exception as exc:
        logger.error("OCR failed for {} page {}: {}", fname, page_num + 1, exc)
        return ""


def extract_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_image(path: Path) -> str:
    """OCR a standalone image file (PNG, JPG, TIFF…)."""
    try:
        import pytesseract
        img = Image.open(path)
        return pytesseract.image_to_string(img, lang="eng")
    except ImportError:
        logger.warning("pytesseract not installed; cannot OCR image {}", path.name)
        return ""
    except Exception as exc:
        logger.error("Image OCR failed for {}: {}", path.name, exc)
        return ""


EXTRACTORS = {
    ".pdf":  extract_pdf,
    ".docx": extract_docx,
    ".doc":  extract_docx,
    ".txt":  extract_txt,
    ".md":   extract_txt,
    ".png":  extract_image,
    ".jpg":  extract_image,
    ".jpeg": extract_image,
    ".tiff": extract_image,
    ".tif":  extract_image,
    ".bmp":  extract_image,
}


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    extractor = EXTRACTORS.get(suffix)
    if extractor is None:
        raise ValueError(f"Unsupported file type: {suffix}")
    return extractor(path)


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


# ── Document ID generation ─────────────────────────────────────────────────────

def doc_id(source_path: Path, chunk_index: int) -> str:
    key = f"{source_path.resolve()}::{chunk_index}"
    return hashlib.sha256(key.encode()).hexdigest()[:24]


# ── Core ingestion function ────────────────────────────────────────────────────

def ingest_file(
    path: Path,
    access_level: AccessLevel,
    collection,
    *,
    extra_metadata: dict | None = None,
) -> int:
    """
    Ingest a single file into Chroma.
    Returns the number of chunks added.
    """
    logger.info("Ingesting: {} [access_level={}]", path.name, access_level)
    raw_text = extract_text(path)
    if not raw_text.strip():
        logger.warning("No text extracted from {}; skipping.", path.name)
        return 0

    chunks = chunk_text(raw_text)
    if not chunks:
        return 0

    ids, documents, metadatas = [], [], []
    for idx, chunk in enumerate(chunks):
        meta = {
            "source": str(path.resolve()),
            "filename": path.name,
            "chunk_index": idx,
            "access_level": access_level.value,  # ← RBAC tag baked in here
            "file_type": path.suffix.lower().lstrip("."),
            "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if extra_metadata:
            meta.update(extra_metadata)

        ids.append(doc_id(path, idx))
        documents.append(chunk)
        metadatas.append(meta)

    # Upsert in batches of 100
    batch = 100
    for start in range(0, len(ids), batch):
        collection.upsert(
            ids=ids[start : start + batch],
            documents=documents[start : start + batch],
            metadatas=metadatas[start : start + batch],
        )

    logger.success("  ✓ {} chunks from {}", len(chunks), path.name)
    return len(chunks)


def ingest_directory(
    directory: Path,
    access_level: AccessLevel,
    collection,
    *,
    recursive: bool = True,
) -> dict[str, int]:
    """
    Walk a directory and ingest all supported files.
    Returns {filename: chunk_count}.
    """
    pattern = "**/*" if recursive else "*"
    files = [
        f for f in directory.glob(pattern)
        if f.is_file() and f.suffix.lower() in EXTRACTORS
    ]
    results: dict[str, int] = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Ingesting documents…", total=len(files))
        for fpath in files:
            try:
                n = ingest_file(fpath, access_level, collection)
                results[fpath.name] = n
            except Exception as exc:
                logger.error("Failed to ingest {}: {}", fpath.name, exc)
                results[fpath.name] = -1
            progress.advance(task)
    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

@app.command()
def ingest(
    path: Path = typer.Argument(..., help="File or directory to ingest"),
    access_level: AccessLevel = typer.Option(
        AccessLevel.PUBLIC, "--access-level", "-a",
        help="RBAC tag to apply to ALL chunks from this path",
    ),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive"),
    extra_meta: str = typer.Option("", "--meta", help="Extra metadata as JSON string"),
):
    """Chunk, embed, and store documents into the Sovereign knowledge base."""
    collection = get_collection()
    extra = json.loads(extra_meta) if extra_meta else None

    if path.is_dir():
        results = ingest_directory(path, access_level, collection, recursive=recursive)
        _print_results_table(results)
    elif path.is_file():
        n = ingest_file(path, access_level, collection, extra_metadata=extra)
        console.print(f"[green]✓[/green] Ingested [bold]{path.name}[/bold] → {n} chunks (access={access_level.value})")
    else:
        console.print(f"[red]Error:[/red] {path} does not exist.")
        raise typer.Exit(1)


@app.command("list")
def list_docs(n: int = typer.Option(50, "--limit", "-n", help="Max records to show")):
    """List recently ingested document chunks in the KB."""
    collection = get_collection()
    results = collection.get(limit=n, include=["metadatas"])
    metas = results.get("metadatas") or []

    # De-duplicate by filename
    seen: dict[str, dict] = {}
    for m in metas:
        fname = m.get("filename", "unknown")
        if fname not in seen:
            seen[fname] = m

    table = Table(title="Sovereign Knowledge Base — Documents")
    table.add_column("Filename", style="cyan")
    table.add_column("Access Level", style="magenta")
    table.add_column("File Type")
    table.add_column("Ingested At")

    for fname, meta in seen.items():
        table.add_row(
            fname,
            meta.get("access_level", "?"),
            meta.get("file_type", "?"),
            meta.get("ingested_at", "?"),
        )
    console.print(table)


@app.command("clear")
def clear_kb(
    confirm: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
):
    """⚠️  Delete ALL documents from the knowledge base (irreversible)."""
    if not confirm:
        typer.confirm("This will delete the entire KB. Are you sure?", abort=True)
    collection = get_collection()
    all_ids = collection.get(include=[])["ids"]
    if all_ids:
        collection.delete(ids=all_ids)
    console.print(f"[yellow]Cleared {len(all_ids)} chunks from the KB.[/yellow]")


def _print_results_table(results: dict[str, int]) -> None:
    table = Table(title="Ingestion Results")
    table.add_column("Filename", style="cyan")
    table.add_column("Chunks", justify="right")
    table.add_column("Status")
    for fname, n in results.items():
        status = "[green]OK[/green]" if n >= 0 else "[red]ERROR[/red]"
        table.add_row(fname, str(n) if n >= 0 else "–", status)
    console.print(table)
    total = sum(n for n in results.values() if n >= 0)
    console.print(f"[bold]Total chunks stored:[/bold] {total}")


if __name__ == "__main__":
    app()
