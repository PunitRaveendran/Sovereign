"""Select the appropriate processor for multimodal inputs."""

from pathlib import Path
from typing import Optional


class ProcessorSelector:
    """Choose OCR or vision processing based on file type and user intent."""

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
    DOCUMENT_EXTENSIONS = {".pdf"}

    OCR_KEYWORDS = {
        "extract text",
        "read text",
        "ocr",
        "transcribe",
        "text from",
        "read the document",
        "read this document",
    }

    VISION_KEYWORDS = {
        "describe",
        "explain",
        "what is shown",
        "what do you see",
        "identify",
        "analyze the image",
        "analyse the image",
        "visual",
        "diagram",
        "drawing",
        "objects",
        "components",
    }

    def select(
        self,
        file_path: str,
        prompt: Optional[str] = None,
    ) -> str:
        """Select the processor for a file and optional user request."""

        suffix = Path(file_path).suffix.lower()

        if suffix not in self.IMAGE_EXTENSIONS | self.DOCUMENT_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}")

        prompt_text = (prompt or "").lower()

        # Explicit OCR request takes priority.
        if any(keyword in prompt_text for keyword in self.OCR_KEYWORDS):
            return "ocr"

        # Explicit visual-understanding request.
        if any(keyword in prompt_text for keyword in self.VISION_KEYWORDS):
            return "vision"

        # PDFs default to vision for now.
        if suffix in self.DOCUMENT_EXTENSIONS:
            return "vision"

        # Images default to OCR.
        return "ocr"