from backend.app.model_ops.model_orchestrator import ModelOrchestrator


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
            "vision": 6000,
            "coding": 5000,
            "general": 3000,
        }

        self.configs = {
            "vision": {
                "category": "vision",
                "model_name": "qwen-vl",
                "backend": "llama.cpp",
            },
            "coding": {
                "category": "coding",
                "model_name": "granite",
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


class FakeSelector:
    def __init__(self, free_mib=7000):
        self.registry = FakeRegistry()
        self.vram_monitor = FakeVRAMMonitor(free_mib)

        from backend.app.model_ops.model_selector import ModelSelector

        self._selector = ModelSelector(
            registry=self.registry,
            vram_monitor=self.vram_monitor,
        )

    def select(self, category):
        return self._selector.select(category)


def create_orchestrator(free_vram=7000):
    vram = FakeVRAMMonitor(free_vram)
    ollama = FakeOllamaController()
    registry = FakeRegistry()

    from backend.app.model_ops.model_manager import ModelManager
    from backend.app.model_ops.model_selector import ModelSelector

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

    return orchestrator, manager, ollama


def test_prepare_model_selects_and_loads_model():
    orchestrator, manager, ollama = create_orchestrator()

    result = orchestrator.prepare_model("vision")

    assert result["status"] == "ready"
    assert result["category"] == "vision"
    assert result["model_name"] == "qwen-vl"
    assert result["required_vram_mib"] == 6000
    assert manager.active_model == "qwen-vl"
    assert "qwen-vl" in ollama.loaded_models


def test_prepare_model_switches_active_model():
    orchestrator, manager, ollama = create_orchestrator()

    manager.active_model = "granite"
    ollama.running_models = ["granite"]

    result = orchestrator.prepare_model("vision")

    assert result["status"] == "ready"
    assert result["model_name"] == "qwen-vl"
    assert "granite" in ollama.stopped_models
    assert "qwen-vl" in ollama.loaded_models
    assert manager.active_model == "qwen-vl"


def test_prepare_model_does_not_reload_active_model():
    orchestrator, manager, ollama = create_orchestrator()

    manager.active_model = "qwen-vl"
    ollama.running_models = ["qwen-vl"]

    result = orchestrator.prepare_model("vision")

    assert result["status"] == "already_active"
    assert result["model_name"] == "qwen-vl"
    assert ollama.loaded_models == []


def test_prepare_model_rejects_when_vram_is_insufficient():
    orchestrator, manager, ollama = create_orchestrator(
        free_vram=5000
    )

    try:
        orchestrator.prepare_model("vision")
        assert False, "Expected RuntimeError"
    except RuntimeError as error:
        assert "Not enough VRAM" in str(error)

    assert ollama.loaded_models == []