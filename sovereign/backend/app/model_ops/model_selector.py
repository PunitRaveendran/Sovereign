"""Automatic model selection for Sovereign."""

from typing import Any, Dict

from backend.app.models.registry import ModelRegistry
from backend.app.model_ops.vram import VRAMMonitor


class ModelSelector:
    """Select a model based on task category and available VRAM."""

    def __init__(
        self,
        registry: ModelRegistry | None = None,
        vram_monitor: VRAMMonitor | None = None,
    ) -> None:
        self.registry = registry or ModelRegistry()
        self.vram_monitor = vram_monitor or VRAMMonitor()

    def get_model_config(self, category: str) -> Dict[str, Any]:
        """Get the configuration for a task category."""
        return self.registry.get_model_config(category)

    def get_required_vram(self, category: str) -> int:
        """Get the VRAM requirement for a task category."""
        return self.registry.get_required_vram(category)

    def can_run(self, category: str) -> bool:
        """Check whether the model for a category fits in available VRAM."""
        required_vram = self.get_required_vram(category)
        usage = self.vram_monitor.get_usage()

        return usage["free_mib"] >= required_vram

    def select(self, category: str) -> Dict[str, Any]:
        """Select a model for the requested task category."""

        config = self.get_model_config(category)
        required_vram = self.get_required_vram(category)

        usage = self.vram_monitor.get_usage()
        free_vram = usage["free_mib"]

        if free_vram < required_vram:
            raise RuntimeError(
                f"Not enough VRAM for category '{category}'. "
                f"Required: {required_vram} MiB, "
                f"Available: {free_vram} MiB."
            )

        return {
            "category": category,
            "model_name": config["model_name"],
            "backend": config["backend"],
            "required_vram_mib": required_vram,
            "available_vram_mib": free_vram,
        }