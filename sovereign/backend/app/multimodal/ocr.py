"""OCR processors for the Sovereign multimodal pipeline."""

from pathlib import Path
from typing import Optional

import pytesseract


class OCRProcessor:
    """Base OCR processor interface."""

    name = "ocr"

    def extract_text(self, image_path: str) -> str:
        """Extract text from an image."""
        raise NotImplementedError


class TesseractOCRProcessor(OCRProcessor):
    """OCR processor using the local Tesseract engine."""

    name = "tesseract"

    def __init__(
        self,
        executable_path: str = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        ),
    ) -> None:
        """Initialize Tesseract."""

        self.executable_path = executable_path
        pytesseract.pytesseract.tesseract_cmd = executable_path

    def extract_text(self, image_path: str) -> str:
        """Extract text from an image using Tesseract."""

        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        text = pytesseract.image_to_string(
            str(path)
        )

        return text.strip()


class MockOCRProcessor(OCRProcessor):
    """Mock OCR processor for development and testing."""

    name = "mock_ocr"

    def extract_text(self, image_path: str) -> str:
        """Return deterministic OCR output."""

        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        return (
            f"[Mock OCR] Text extracted from "
            f"{path.name}"
        )