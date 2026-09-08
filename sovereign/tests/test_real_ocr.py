from pathlib import Path

from PIL import Image, ImageDraw

from backend.app.multimodal.ocr import TesseractOCRProcessor
from backend.app.multimodal.pipeline import MultimodalPipeline


def create_test_image(tmp_path):
    """Create an image containing known text for OCR testing."""

    image_path = Path(tmp_path) / "ocr_test.png"

    image = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(image)

    draw.text(
        (50, 70),
        "Safety inspection every 30 days",
        fill="black",
    )

    image.save(image_path)

    return str(image_path)


def test_real_tesseract_ocr(tmp_path):
    """Verify that Tesseract extracts text from a real image."""

    image_path = create_test_image(tmp_path)

    ocr = TesseractOCRProcessor()

    text = ocr.extract_text(image_path)

    assert "Safety inspection" in text
    assert "30 days" in text


def test_pipeline_with_real_tesseract(tmp_path):
    """Verify the complete pipeline using real Tesseract."""

    image_path = create_test_image(tmp_path)

    ocr = TesseractOCRProcessor()

    pipeline = MultimodalPipeline(
        ocr_engine=ocr,
    )

    result = pipeline.process(image_path)

    assert result["type"] == "image"
    assert result["processor"] == "ocr"
    assert result["status"] == "ready"
    assert "Safety inspection" in result["text"]
    assert "30 days" in result["text"]