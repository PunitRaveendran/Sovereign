"""Unified Multimodal Pipeline for Sovereign."""

from pathlib import Path
from typing import Any, Dict, Optional

from app.multimodal.ocr import TesseractOCRProcessor
from app.multimodal.vision import QwenVisionModel


class MultimodalPipeline:
    """Process images, scans, and documents for the Sovereign Agent."""

    SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}
    SUPPORTED_DOCUMENT_TYPES = {".pdf", ".txt"}

    def __init__(
        self,
        vision_model: Optional[QwenVisionModel] = None,
        ocr_engine: Optional[TesseractOCRProcessor] = None,
    ) -> None:
        self.ocr_engine = ocr_engine or TesseractOCRProcessor()
        self.vision_model = vision_model or QwenVisionModel(ocr_fallback=self.ocr_engine)

    def validate_file(self, file_path: str) -> bool:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        return (
            suffix in self.SUPPORTED_IMAGE_TYPES
            or suffix in self.SUPPORTED_DOCUMENT_TYPES
        )

    def process(
        self,
        file_path: str,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process an uploaded image or scanned document."""
        self.validate_file(file_path)
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in self.SUPPORTED_IMAGE_TYPES:
            extracted_analysis = self.vision_model.process(str(path), prompt=prompt)
            return {
                "file": path.name,
                "type": "image",
                "processor": "vision_qwen",
                "extracted_text": extracted_analysis,
                "status": "success",
            }
        else:
            extracted_text = self.ocr_engine.extract_text(str(path))
            return {
                "file": path.name,
                "type": "document",
                "processor": "ocr_tesseract",
                "extracted_text": extracted_text,
                "status": "success",
            }
