"""Multimodal input pipeline for Sovereign."""

from pathlib import Path
from typing import Any, Dict, Optional

from backend.app.multimodal.processor_selector import ProcessorSelector


class MultimodalPipeline:
    """Process images and scanned documents."""

    SUPPORTED_IMAGE_TYPES = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }

    SUPPORTED_DOCUMENT_TYPES = {
        ".pdf",
    }

    def __init__(
        self,
        vision_model: Optional[Any] = None,
        ocr_engine: Optional[Any] = None,
    ) -> None:
        """Initialize the multimodal pipeline."""

        self.vision_model = vision_model
        self.ocr_engine = ocr_engine
        self.selector = ProcessorSelector()

    def validate_file(self, file_path: str) -> bool:
        """Check whether the file type is supported."""

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

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
        """Process an image or scanned document."""

        self.validate_file(file_path)

        path = Path(file_path)

        processor_type = self.selector.select(
            file_path=file_path,
            prompt=prompt,
            )

        result: Dict[str, Any] = {
            "file": str(path),
            "type": (
                "image"
                if path.suffix.lower()
                in self.SUPPORTED_IMAGE_TYPES
                else "document"
            ),
            "processor": processor_type,
            "vision_model": (
                type(self.vision_model).__name__
                if self.vision_model
                else None
            ),
            "ocr_engine": (
                type(self.ocr_engine).__name__
                if self.ocr_engine
                else None
            ),
            "status": "ready",
            "text": None,
        }

        if processor_type == "ocr":
            if self.ocr_engine is None:
                result["status"] = "ocr_unavailable"
            else:
                result["text"] = (
                    self.ocr_engine.extract_text(
                        file_path
                    )
                )

        elif processor_type == "vision":
            if self.vision_model is None:
                result["status"] = "vision_unavailable"
            else:
                if prompt is None:
                    prompt = "Describe this image."

                result["text"] = (
                    self.vision_model.process(
                        file_path,
                        prompt,
                    )
                )

        return result