"""Unit tests for the task router classification."""

import sys
from pathlib import Path

# Ensure project root is on sys.path for backend package imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.router.task_router import (
    CATEGORY_CODING,
    CATEGORY_DOCUMENT,
    CATEGORY_GENERAL,
    CATEGORY_VISION,
    classify_task,
)


def test_coding_category():
    """Verify coding and programming prompts are classified as 'coding'."""
    assert classify_task("write Python code") == CATEGORY_CODING
    assert classify_task("debug this Java program") == CATEGORY_CODING
    assert classify_task("Create a SQL query for customer orders") == CATEGORY_CODING
    assert classify_task("Refactor this function to improve performance") == CATEGORY_CODING


def test_vision_category():
    """Verify image and scan-related prompts are classified as 'vision'."""
    assert classify_task("read this scanned report") == CATEGORY_VISION
    assert classify_task("analyze this image") == CATEGORY_VISION
    assert classify_task("Extract text from this screenshot using OCR") == CATEGORY_VISION
    assert classify_task("Inspect this diagram for defects") == CATEGORY_VISION


def test_document_category():
    """Verify document, policy, and summarization prompts are classified as 'document'."""
    assert classify_task("summarize this SOP document") == CATEGORY_DOCUMENT
    assert classify_task("explain this company policy") == CATEGORY_DOCUMENT
    assert classify_task("Review the safety guideline handbook") == CATEGORY_DOCUMENT
    assert classify_task("Provide a summary of the compliance report") == CATEGORY_DOCUMENT


def test_general_category():
    """Verify miscellaneous and unspecific prompts fall back to 'general'."""
    assert classify_task("Hello, how are you?") == CATEGORY_GENERAL
    assert classify_task("What is the capital of France?") == CATEGORY_GENERAL
    assert classify_task("Tell me an interesting historical fact") == CATEGORY_GENERAL
    assert classify_task("anything else") == CATEGORY_GENERAL


def test_edge_cases():
    """Verify edge cases such as empty input, whitespace, and non-string types."""
    assert classify_task("") == CATEGORY_GENERAL
    assert classify_task("   ") == CATEGORY_GENERAL
    assert classify_task(None) == CATEGORY_GENERAL  # type: ignore
