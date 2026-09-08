"""Task Router Module.

Classifies incoming user input into predefined task categories:
- coding: Programming, debugging, and code-related requests.
- vision: Image, scan, and visual inspection requests.
- document: Reading, summarizing, and analyzing policies, manuals, or SOPs.
- general: General queries or anything that does not match specific rules.
"""

from typing import List

# Predefined task categories
CATEGORY_CODING = "coding"
CATEGORY_DOCUMENT = "document"
CATEGORY_VISION = "vision"
CATEGORY_GENERAL = "general"

TASK_CATEGORIES: List[str] = [
    CATEGORY_CODING,
    CATEGORY_DOCUMENT,
    CATEGORY_VISION,
    CATEGORY_GENERAL,
]

# Keywords associated with vision / image-based tasks
VISION_KEYWORDS = [
    "image",
    "photo",
    "picture",
    "scan",
    "scanned",
    "diagram",
    "screenshot",
    "ocr",
    "visual",
]

# Keywords associated with coding / software engineering tasks
CODING_KEYWORDS = [
    "code",
    "python",
    "java",
    "c++",
    "rust",
    "javascript",
    "typescript",
    "debug",
    "programming",
    "program",
    "function",
    "script",
    "algorithm",
    "bug",
    "refactor",
    "sql",
]

# Keywords associated with document / policy processing tasks
DOCUMENT_KEYWORDS = [
    "document",
    "sop",
    "policy",
    "report",
    "summarize",
    "summary",
    "pdf",
    "manual",
    "contract",
    "guideline",
    "procedure",
    "handbook",
]


def classify_task(user_input: str) -> str:
    """Classify user input into one of the predefined task categories.

    Uses a rule-based keyword matching approach:
    1. Checks for vision/image keywords (e.g., scanned reports, photos, screenshots).
    2. Checks for coding keywords (e.g., python code, debug program).
    3. Checks for document keywords (e.g., SOP documents, company policies).
    4. Defaults to 'general' if no specific keywords match.

    Args:
        user_input: The raw prompt or task description from the user.

    Returns:
        A string representing the category:
        'coding', 'vision', 'document', or 'general'.
    """
    if not user_input or not isinstance(user_input, str):
        return CATEGORY_GENERAL

    normalized_input = user_input.lower()

    # 1. Vision tasks (scans, images, visual artifacts)
    if any(keyword in normalized_input for keyword in VISION_KEYWORDS):
        return CATEGORY_VISION

    # 2. Coding tasks (writing code, debugging, programming)
    if any(keyword in normalized_input for keyword in CODING_KEYWORDS):
        return CATEGORY_CODING

    # 3. Document tasks (SOPs, policies, summaries)
    if any(keyword in normalized_input for keyword in DOCUMENT_KEYWORDS):
        return CATEGORY_DOCUMENT

    # 4. Default fallback category
    return CATEGORY_GENERAL
