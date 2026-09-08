from pathlib import Path

from backend.app.multimodal.pipeline import MultimodalPipeline


class FakeOCR:
    def extract_text(self, file_path):
        return "Safety inspection every 30 days"


class FakeVision:
    def process(self, file_path, prompt):
        return f"Vision analysis for: {prompt}"


def create_file(tmp_path, filename):
    file_path = Path(tmp_path) / filename
    file_path.write_text("test content")
    return str(file_path)


def test_pipeline_uses_ocr_for_image(tmp_path):
    image = create_file(tmp_path, "scan.png")

    pipeline = MultimodalPipeline(
        ocr_engine=FakeOCR(),
        vision_model=FakeVision(),
    )

    result = pipeline.process(image)

    assert result["type"] == "image"
    assert result["processor"] == "ocr"
    assert result["status"] == "ready"
    assert result["text"] == "Safety inspection every 30 days"


def test_pipeline_uses_vision_for_visual_request(tmp_path):
    image = create_file(tmp_path, "drawing.png")

    pipeline = MultimodalPipeline(
        ocr_engine=FakeOCR(),
        vision_model=FakeVision(),
    )

    result = pipeline.process(
        image,
        "Describe this image.",
    )

    assert result["type"] == "image"
    assert result["processor"] == "vision"
    assert result["status"] == "ready"
    assert "Describe this image." in result["text"]


def test_pipeline_uses_vision_for_pdf(tmp_path):
    document = create_file(tmp_path, "document.pdf")

    pipeline = MultimodalPipeline(
        ocr_engine=FakeOCR(),
        vision_model=FakeVision(),
    )

    result = pipeline.process(document)

    assert result["type"] == "document"
    assert result["processor"] == "vision"
    assert result["status"] == "ready"


def test_pipeline_reports_missing_ocr_engine(tmp_path):
    image = create_file(tmp_path, "scan.jpg")

    pipeline = MultimodalPipeline(
        vision_model=FakeVision(),
    )

    result = pipeline.process(image)

    assert result["processor"] == "ocr"
    assert result["status"] == "ocr_unavailable"
    assert result["text"] is None


def test_pipeline_reports_missing_vision_model(tmp_path):
    image = create_file(tmp_path, "drawing.png")

    pipeline = MultimodalPipeline()

    result = pipeline.process(
        image,
        "Describe this image.",
    )

    assert result["processor"] == "vision"
    assert result["status"] == "vision_unavailable"
    assert result["text"] is None


def test_pipeline_rejects_unsupported_file(tmp_path):
    text_file = create_file(tmp_path, "notes.txt")

    pipeline = MultimodalPipeline()

    try:
        pipeline.process(text_file)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Unsupported file type" in str(error)