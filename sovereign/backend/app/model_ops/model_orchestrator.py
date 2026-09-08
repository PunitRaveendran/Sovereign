"""Coordinate model selection and model lifecycle management."""

from typing import Optional

from backend.app.model_ops.model_manager import ModelManager
from backend.app.model_ops.model_selector import ModelSelector


class ModelOrchestrator:
    """Automatically select and activate the appropriate model."""

    def __init__(
        self,
        selector: Optional[ModelSelector] = None,
        manager: Optional[ModelManager] = None,
    ) -> None:
        self.selector = selector or ModelSelector()
        self.manager = manager or ModelManager()

    def prepare_model(self, category: str) -> dict:
        """Select and prepare the model required for a task."""

        selection = self.selector.select(category)

        model_name = selection["model_name"]
        required_vram = selection["required_vram_mib"]

        current_model = self.manager.active_model

        if current_model == model_name:
            return {
                "status": "already_active",
                **selection,
            }

        result = self.manager.switch_model(
            current_model=current_model,
            new_model=model_name,
            required_vram_mib=required_vram,
        )

        return {
            "status": "ready",
            "result": result,
            **selection,
        }

    def get_active_model(self):
        """Return the currently active model."""

        return self.manager.get_active_model()