from backend.app.model_ops.model_manager import ModelManager


class FakeVRAMMonitor:
    """Fake GPU monitor for testing."""

    def __init__(self, free_mib=7000):
        self.free_mib = free_mib

    def get_usage(self):
        return {
            "total_mib": 8188,
            "used_mib": 8188 - self.free_mib,
            "free_mib": self.free_mib,
        }


class FakeOllamaController:
    """Fake Ollama controller for testing."""

    def __init__(self):
        self.running_models = []
        self.stopped_models = []
        self.loaded_models = []

    def list_running_models(self):
        return self.running_models.copy()

    def is_running(self, model_name):
        return model_name in self.running_models

    def stop_model(self, model_name):
        if model_name in self.running_models:
            self.running_models.remove(model_name)

        self.stopped_models.append(model_name)

    def run_model(self, model_name, prompt):
        self.running_models.append(model_name)
        self.loaded_models.append(model_name)

        return "model loaded"


class FakeRegistry:
    """Fake model registry for testing."""

    def __init__(self):
        self.vram_requirements = {
            "vision": 6000,
            "coding": 5000,
            "general": 3000,
        }

    def get_required_vram(self, category):
        return self.vram_requirements[category]


def create_manager(free_vram=7000):
    """Create a ModelManager using fake dependencies."""

    vram = FakeVRAMMonitor(free_vram)
    ollama = FakeOllamaController()
    registry = FakeRegistry()

    manager = ModelManager(
        vram_monitor=vram,
        ollama_controller=ollama,
        model_registry=registry,
    )

    return manager, vram, ollama


def test_can_load_model_when_enough_vram():
    manager, _, _ = create_manager(free_vram=7000)

    assert manager.can_load_category("vision") is True


def test_rejects_model_when_vram_is_insufficient():
    manager, _, _ = create_manager(free_vram=5000)

    assert manager.can_load_category("vision") is False


def test_load_model():
    manager, _, ollama = create_manager(free_vram=7000)

    result = manager.load_model(
        "test-model",
        6000,
    )

    assert result == "test-model loaded successfully."
    assert "test-model" in ollama.loaded_models
    assert manager.active_model == "test-model"


def test_switch_model():
    manager, _, ollama = create_manager(free_vram=7000)

    ollama.running_models = ["old-model"]

    result = manager.switch_model(
        "old-model",
        "new-model",
        6000,
    )

    assert result == "new-model loaded successfully."
    assert "old-model" in ollama.stopped_models
    assert "new-model" in ollama.loaded_models
    assert manager.active_model == "new-model"


def test_load_model_rejected_when_vram_is_insufficient():
    manager, _, ollama = create_manager(free_vram=4000)

    result = manager.load_model(
        "large-model",
        6000,
    )

    assert "Not enough VRAM" in result
    assert "large-model" not in ollama.loaded_models


def test_model_registry_vram_requirement():
    manager, _, _ = create_manager()

    assert manager.get_required_vram("vision") == 6000
    assert manager.get_required_vram("coding") == 5000
    assert manager.get_required_vram("general") == 3000