"""OCR processors for the Sovereign multimodal pipeline."""

import os
import shutil
from pathlib import Path
from typing import Optional

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from rapidocr_onnxruntime import RapidOCR
    rapid_ocr_engine = RapidOCR()
except Exception:
    rapid_ocr_engine = None


class OCRProcessor:
    """Base OCR processor interface."""

    name = "ocr"

    def extract_text(self, image_path: str) -> str:
        """Extract text from an image."""
        raise NotImplementedError


class TesseractOCRProcessor(OCRProcessor):
    """OCR processor using the local Tesseract engine with resilient fallbacks."""

    name = "tesseract"

    def __init__(
        self,
        executable_path: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    ) -> None:
        """Initialize Tesseract."""
        self.executable_path = executable_path
        
        # Check standard installation locations
        search_paths = [
            executable_path,
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            shutil.which("tesseract") or "",
        ]
        
        self.available_path = None
        for p in search_paths:
            if p and os.path.exists(p):
                self.available_path = p
                break
                
        if self.available_path and pytesseract:
            pytesseract.pytesseract.tesseract_cmd = self.available_path

    def extract_text(self, image_path: str) -> str:
        """Extract text from an image using Tesseract or document parser."""
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {image_path}")

        # PDF handling via text extraction (PyMuPDF or pypdf)
        if path.suffix.lower() == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(path))
                text_parts = [page.get_text() for page in doc]
                full_text = "\n".join(text_parts).strip()
                if full_text:
                    return full_text
            except Exception:
                pass
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                text_parts = [page.extract_text() or "" for page in reader.pages]
                full_text = "\n".join(text_parts).strip()
                if full_text:
                    return full_text
            except Exception:
                pass

        # RapidOCR neural engine (on-device, pure Python / ONNX)
        if rapid_ocr_engine and path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            try:
                ocr_res, _ = rapid_ocr_engine(str(path))
                if ocr_res:
                    lines = [item[1] for item in ocr_res if item and len(item) > 1]
                    full_text = "\n".join(lines).strip()
                    if full_text:
                        return full_text
            except Exception:
                pass

        # Check if tesseract executable became available in standard locations
        if not self.available_path:
            for p in [
                self.executable_path,
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
                shutil.which("tesseract") or "",
            ]:
                if p and os.path.exists(p):
                    self.available_path = p
                    if pytesseract:
                        pytesseract.pytesseract.tesseract_cmd = p
                    break

        # Real Tesseract if installed
        if self.available_path and pytesseract:
            try:
                from PIL import Image
                img = Image.open(str(path))
                text = pytesseract.image_to_string(img)
                if text and text.strip():
                    return text.strip()
            except Exception:
                pass

        # Text document reading (for .txt or plaintext logs)
        if path.suffix.lower() in [".txt", ".log", ".csv", ".json", ".md"]:
            try:
                return path.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                pass

        return f"[OCR_EXTRACTION_UNAVAILABLE: No machine-readable text could be extracted from {path.name}. Optical OCR failed or no text found.]"
