"""VRAM-aware model lifecycle management for Sovereign."""

from typing import Dict, Optional

from backend.app.model_ops.ollama_controller import OllamaController
from backend.app.model_ops.vram import VRAMMonitor
from backend.app.models.registry import ModelRegistry


class ModelManager:
    """Manage local models while considering GPU VRAM."""

    def __init__(
        self,
        vram_monitor: Optional[VRAMMonitor] = None,
        ollama_controller: Optional[OllamaController] = None,
        model_registry: Optional[ModelRegistry] = None,
    ) -> None:
        self.loaded_models: Dict[str, object] = {}
        self.active_model: Optional[str] = None

        self.vram_monitor = vram_monitor or VRAMMonitor()
        self.ollama = ollama_controller or OllamaController()
        self.registry = model_registry or ModelRegistry()

    def register_model(self, name: str, model: object) -> None:
        """Register a model with the manager."""
        self.loaded_models[name] = model

    def can_load(self, required_vram_mib: int) -> bool:
        """Check whether enough free VRAM is available."""
        usage = self.vram_monitor.get_usage()
        return usage["free_mib"] >= required_vram_mib

    def can_load_category(self, category: str) -> bool:
        """Check whether a configured model fits in available VRAM."""
        required_vram = self.registry.get_required_vram(category)
        return self.can_load(required_vram)

    def get_required_vram(self, category: str) -> int:
        """Get the configured VRAM requirement."""
        return self.registry.get_required_vram(category)

    def load_model(
        self,
        model_name: str,
        required_vram_mib: int,
    ) -> str:
        """Load a model through Ollama after checking VRAM."""

        if self.ollama.is_running(model_name):
            self.active_model = model_name
            return f"{model_name} is already running."

        if not self.can_load(required_vram_mib):
            usage = self.vram_monitor.get_usage()

            return (
                f"Not enough VRAM for {model_name}. "
                f"Required: {required_vram_mib} MiB, "
                f"Free: {usage['free_mib']} MiB."
            )

        self.ollama.run_model(
            model_name,
            "Reply with exactly: model loaded.",
        )

        if not self.ollama.is_running(model_name):
            return f"Failed to verify that {model_name} is running."

        self.active_model = model_name

        return f"{model_name} loaded successfully."

    def activate(self, name: str) -> object:
        """Activate a registered model."""
        if name not in self.loaded_models:
            raise KeyError(f"Model '{name}' is not registered.")

        self.active_model = name
        return self.loaded_models[name]

    def switch_model(
        self,
        current_model: Optional[str],
        new_model: str,
        required_vram_mib: int,
    ) -> str:
        """Switch from one Ollama model to another."""

        if current_model == new_model:
            self.active_model = new_model
            return f"{new_model} is already active."

        if current_model and self.ollama.is_running(current_model):
            self.ollama.stop_model(current_model)

        return self.load_model(
            new_model,
            required_vram_mib,
        )

    def get_active_model(self) -> object:
        """Return the currently active registered model."""
        if self.active_model is None:
            raise RuntimeError("No model is currently active.")

        if self.active_model not in self.loaded_models:
            raise KeyError(
                f"Active model '{self.active_model}' is not registered."
            )

        return self.loaded_models[self.active_model]

    def unload(self, name: str) -> None:
        """Unload a model from Ollama and the manager."""

        if self.ollama.is_running(name):
            self.ollama.stop_model(name)

        if name in self.loaded_models:
            del self.loaded_models[name]

        if self.active_model == name:
            self.active_model = None

    def list_models(self) -> list[str]:
        """Return models registered with the manager."""
        return list(self.loaded_models.keys())

    def list_running_models(self) -> list[str]:
        """Return models currently running in Ollama."""
        return self.ollama.list_running_models()