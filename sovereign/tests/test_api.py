from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


class FakeTaskService:
    def execute(self, prompt, file_path=None):
        result = {
            "category": "general",
            "response": f"Fake response for: {prompt}",
            "model_name": "phi-4-mini",
            "backend": "llama.cpp",
        }

        if file_path is not None:
            result["file_received"] = True
            result["file_name"] = Path(file_path).name

        return result


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "sovereign"


def test_task_endpoint(monkeypatch):
    monkeypatch.setattr(
        "backend.app.main.get_task_service",
        lambda: FakeTaskService(),
    )

    response = client.post(
        "/task",
        json={"prompt": "Hello, how are you?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["category"] == "general"
    assert data["model_name"] == "phi-4-mini"
    assert data["backend"] == "llama.cpp"

    assert "response" in data
    assert "Hello, how are you?" in data["response"]


def test_task_upload_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "backend.app.main.get_task_service",
        lambda: FakeTaskService(),
    )

    test_file = tmp_path / "test_scan.png"
    test_file.write_bytes(b"fake image content")

    with test_file.open("rb") as file:
        response = client.post(
            "/task/upload",
            data={
                "prompt": "Extract text from this image.",
            },
            files={
                "file": (
                    "test_scan.png",
                    file,
                    "image/png",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["file_received"] is True
    assert data["file_name"].endswith(".png")
    assert "Extract text from this image." in data["response"]


def test_task_upload_rejects_unsupported_file(monkeypatch):
    monkeypatch.setattr(
        "backend.app.main.get_task_service",
        lambda: FakeTaskService(),
    )

    response = client.post(
        "/task/upload",
        data={
            "prompt": "Read this file.",
        },
        files={
            "file": (
                "malware.exe",
                b"fake executable",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "error" in data
    assert "Unsupported file type" in data["error"]

def test_task_upload_with_real_ocr(tmp_path, monkeypatch):
    """Test the upload endpoint with the real Tesseract OCR."""

    from backend.app.multimodal.ocr import TesseractOCRProcessor
    from backend.app.multimodal.pipeline import MultimodalPipeline

    class FakeTaskService:
        def __init__(self):
            self.pipeline = MultimodalPipeline(
                ocr_engine=TesseractOCRProcessor()
            )

        def execute(self, prompt, file_path=None):
            multimodal_result = self.pipeline.process(
                file_path=file_path,
                prompt=prompt,
            )

            return {
                "category": "vision",
                "response": multimodal_result["text"],
                "model_name": "qwen2.5-vl-7b",
                "backend": "llama.cpp",
                "multimodal": multimodal_result,
            }

    monkeypatch.setattr(
        "backend.app.main.get_task_service",
        lambda: FakeTaskService(),
    )

    test_file = Path("test_scan.png")

    with test_file.open("rb") as file:
        response = client.post(
            "/task/upload",
            data={
                "prompt": "Extract text from this image.",
            },
            files={
                "file": (
                    "test_scan.png",
                    file,
                    "image/png",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert "multimodal" in data
    assert data["multimodal"]["processor"] == "ocr"
    assert "Safety inspection every 30 days" in data["multimodal"]["text"]