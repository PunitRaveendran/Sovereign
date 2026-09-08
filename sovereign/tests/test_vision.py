from pathlib import Path

from backend.app.multimodal.vision import (
    MockVisionModel,
    QwenVisionModel,
)


def create_test_image(tmp_path):
    """Create a simple test file representing an image."""

    image_path = Path(tmp_path) / "test_image.png"
    image_path.write_bytes(b"fake image content")

    return str(image_path)


def test_mock_vision_model_processes_image(tmp_path):
    image_path = create_test_image(tmp_path)

    model = MockVisionModel()

    result = model.process(
        image_path,
        "Describe this image.",
    )

    assert "test_image.png" in result
    assert "Describe this image." in result


def test_mock_vision_model_default_prompt(tmp_path):
    image_path = create_test_image(tmp_path)

    model = MockVisionModel()

    result = model.process(image_path)

    assert "Describe this image." in result


def test_qwen_vision_model_configuration():
    model = QwenVisionModel()

    assert model.model_name == "qwen2.5-vl-7b"
    assert model.backend == "llama.cpp"
    assert model.name == "qwen2.5-vl"


def test_qwen_vision_model_accepts_custom_configuration():
    model = QwenVisionModel(
        model_name="qwen2.5-vl-7b-q4",
        backend="llama.cpp",
        config={
            "quantization": "Q4",
            "required_vram_mib": 6000,
        },
    )

    assert model.model_name == "qwen2.5-vl-7b-q4"
    assert model.config["quantization"] == "Q4"
    assert model.config["required_vram_mib"] == 6000


def test_qwen_vision_model_rejects_missing_image(tmp_path):
    model = QwenVisionModel()

    missing_image = str(
        Path(tmp_path) / "does_not_exist.png"
    )

    try:
        model.process(missing_image)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError as error:
        assert "Image not found" in str(error)


def test_qwen_vision_model_reports_unimplemented_inference(tmp_path):
    image_path = create_test_image(tmp_path)

    model = QwenVisionModel()

    try:
        model.process(
            image_path,
            "Describe this image.",
        )
        assert False, "Expected NotImplementedError"
    except NotImplementedError as error:
        assert "Qwen2.5-VL inference is not connected yet" in str(error)