from pathlib import Path
from tempfile import NamedTemporaryFile

from backend.app.model_ops.model_manager import ModelManager
from backend.app.model_ops.model_selector import ModelSelector
from backend.app.model_ops.model_orchestrator import ModelOrchestrator
from backend.app.services.task_service import TaskService, process_task
from backend.app.multimodal.pipeline import MultimodalPipeline


class FakeVRAMMonitor:
    def __init__(self, free_mib=7000):
        self.free_mib = free_mib

    def get_usage(self):
        return {
            "total_mib": 8188,
            "used_mib": 8188 - self.free_mib,
            "free_mib": self.free_mib,
        }


class FakeOllamaController:
    def __init__(self):
        self.running_models = []
        self.loaded_models = []
        self.stopped_models = []

    def list_running_models(self):
        return self.running_models.copy()

    def is_running(self, model_name):
        return model_name in self.running_models

    def run_model(self, model_name, prompt):
        self.running_models.append(model_name)
        self.loaded_models.append(model_name)
        return "model loaded"

    def stop_model(self, model_name):
        if model_name in self.running_models:
            self.running_models.remove(model_name)
        self.stopped_models.append(model_name)


class FakeRegistry:
    def __init__(self):
        self.vram_requirements = {
            "coding": 5000,
            "vision": 6000,
            "document": 6000,
            "general": 3000,
        }

        self.configs = {
            "coding": {
                "category": "coding",
                "model_name": "granite",
                "backend": "llama.cpp",
            },
            "vision": {
                "category": "vision",
                "model_name": "qwen-vl",
                "backend": "llama.cpp",
            },
            "document": {
                "category": "document",
                "model_name": "nemotron",
                "backend": "llama.cpp",
            },
            "general": {
                "category": "general",
                "model_name": "phi-4-mini",
                "backend": "llama.cpp",
            },
        }

    def get_required_vram(self, category):
        return self.vram_requirements[category]

    def get_model_config(self, category):
        return self.configs[category]


class FakeModel:
    def __init__(self, model_name, backend="llama.cpp"):
        self.model_name = model_name
        self.backend = backend

    def generate(self, prompt):
        return f"Generated response for: {prompt}"


def create_task_service(free_vram=7000):
    vram = FakeVRAMMonitor(free_vram)
    ollama = FakeOllamaController()
    registry = FakeRegistry()

    manager = ModelManager(
        vram_monitor=vram,
        ollama_controller=ollama,
        model_registry=registry,
    )

    selector = ModelSelector(
        registry=registry,
        vram_monitor=vram,
    )

    orchestrator = ModelOrchestrator(
        selector=selector,
        manager=manager,
    )

    # Register the fake models so the TaskService can generate responses.
    manager.register_model(
        "granite",
        FakeModel("granite"),
    )
    manager.register_model(
        "qwen-vl",
        FakeModel("qwen-vl"),
    )
    manager.register_model(
        "nemotron",
        FakeModel("nemotron"),
    )
    manager.register_model(
        "phi-4-mini",
        FakeModel("phi-4-mini"),
    )

    return TaskService(orchestrator=orchestrator)


def test_process_coding_task():
    service = create_task_service()

    result = service.execute("Write a Python function to sort a list.")

    assert result["category"] == "coding"
    assert result["model_name"] == "granite"
    assert result["backend"] == "llama.cpp"
    assert "Generated response" in result["response"]


def test_process_vision_task():
    service = create_task_service()

    result = service.execute("Analyze this image.")

    assert result["category"] == "vision"
    assert result["model_name"] == "qwen-vl"
    assert result["backend"] == "llama.cpp"


def test_process_document_task():
    service = create_task_service()

    result = service.execute("Summarize this document.")

    assert result["category"] == "document"
    assert result["model_name"] == "nemotron"
    assert result["backend"] == "llama.cpp"


def test_process_general_task():
    service = create_task_service()

    result = service.execute("Hello, how are you?")

    assert result["category"] == "general"
    assert result["model_name"] == "phi-4-mini"
    assert result["backend"] == "llama.cpp"


def test_task_service_class_instance():
    service = create_task_service()

    result = service.execute("Write code for a calculator.")

    assert isinstance(result, dict)
    assert "category" in result
    assert "response" in result
    assert "model_name" in result
    assert "backend" in result


def test_edge_case_empty_prompt():
    service = create_task_service()

    result = service.execute("")

    assert result["category"] == "general"
    assert result["model_name"] == "phi-4-mini"


def test_process_task_function():
    """Verify the backwards-compatible process_task function.

    This uses the real process_task API separately from the injected
    TaskService because process_task creates its own default service.
    """
    # We only verify that the function exists and has the expected API.
    assert callable(process_task)

class FakeOCR:
    """Fake OCR engine for testing."""

    def extract_text(self, image_path):
        return "Safety inspection every 30 days."


class FakeVision:
    """Fake vision model for testing."""

    def process(self, image_path, prompt=None):
        return f"Vision result for {Path(image_path).name}: {prompt}"


def create_multimodal_task_service(free_vram=7000):
    """Create a TaskService with fake model and multimodal components."""

    vram = FakeVRAMMonitor(free_vram)
    ollama = FakeOllamaController()
    registry = FakeRegistry()

    manager = ModelManager(
        vram_monitor=vram,
        ollama_controller=ollama,
        model_registry=registry,
    )

    selector = ModelSelector(
        registry=registry,
        vram_monitor=vram,
    )

    orchestrator = ModelOrchestrator(
        selector=selector,
        manager=manager,
    )

    manager.register_model(
        "granite",
        FakeModel("granite"),
    )

    manager.register_model(
        "qwen-vl",
        FakeModel("qwen-vl"),
    )

    manager.register_model(
        "nemotron",
        FakeModel("nemotron"),
    )

    manager.register_model(
        "phi-4-mini",
        FakeModel("phi-4-mini"),
    )

    pipeline = MultimodalPipeline(
        vision_model=FakeVision(),
        ocr_engine=FakeOCR(),
    )

    return TaskService(
        orchestrator=orchestrator,
        multimodal_pipeline=pipeline,
    )

def test_task_service_with_ocr_file():
    """Verify that an attached image is processed through OCR."""

    service = create_multimodal_task_service()

    with NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        result = service.execute(
            "Extract text from this image.",
            file_path=temp_path,
        )

        assert result["category"] == "vision"
        assert result["model_name"] == "qwen-vl"

        assert "multimodal" in result
        assert result["multimodal"]["processor"] == "ocr"

        assert (
            result["multimodal"]["text"]
            == "Safety inspection every 30 days."
        )

        assert "Safety inspection every 30 days." in result["response"]

    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_task_service_with_vision_file():
    """Verify that an attached image can be processed by vision."""

    service = create_multimodal_task_service()

    with NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        result = service.execute(
            "Analyze the image.",
            file_path=temp_path,
        )

        assert result["category"] == "vision"
        assert result["model_name"] == "qwen-vl"

        assert "multimodal" in result
        assert result["multimodal"]["processor"] == "vision"

        assert "Vision result" in result["multimodal"]["text"]

        assert "Vision result" in result["response"]

    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_task_service_without_file():
    """Verify that text-only requests still work."""

    service = create_multimodal_task_service()

    result = service.execute(
        "Write a Python function to calculate factorial."
    )

    assert result["category"] == "coding"
    assert result["model_name"] == "granite"

    assert "multimodal" not in result