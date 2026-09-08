"""Vision model interfaces for the Sovereign multimodal pipeline."""

from pathlib import Path
from typing import Any, Dict, Optional

from backend.app.models.base import BaseModel


class VisionModel(BaseModel):
    """Base interface for a local vision-language model."""

    name = "vision_model"

    def process(self, image_path: str, prompt: Optional[str] = None) -> str:
        raise NotImplementedError


class MockVisionModel(VisionModel):
    """Mock vision model for local development and testing."""

    name = "mock_qwen_vl"

    def __init__(
        self,
        model_name: str = "mock-qwen2.5-vl",
        backend: str = "mock",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(model_name=model_name)
        self.backend = backend
        self.config = config or {}

    def process(
        self,
        image_path: str,
        prompt: Optional[str] = None,
    ) -> str:
        path = Path(image_path)

        if prompt is None:
            prompt = "Describe this image."

        return (
            f"[Mock Vision] Processed {path.name} "
            f"with prompt: {prompt}"
        )

    def generate(self, prompt: str) -> str:
        """Provide BaseModel-compatible generation for testing."""
        return (
            f"[{self.model_name} via {self.backend}] "
            f"Generated response for: {prompt}"
            )


class QwenVisionModel(VisionModel):
    """Interface for the local Qwen2.5-VL vision-language model.

    The actual model loading and inference will be implemented and tested
    on the NVIDIA GPU machine. This adapter keeps the rest of Sovereign
    independent of the underlying Qwen implementation.
    """

    name = "qwen2.5-vl"

    def __init__(
        self,
        model_name: str = "qwen2.5-vl-7b",
        backend: str = "llama.cpp",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(model_name=model_name)
        self.backend = backend
        self.config = config or {}

    def process(
        self,
        image_path: str,
        prompt: Optional[str] = None,
    ) -> str:
        """Process an image using Qwen2.5-VL.

        Actual inference will be connected later on the GPU machine.
        """
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        if prompt is None:
            prompt = "Describe this image."

        raise NotImplementedError(
            "Qwen2.5-VL inference is not connected yet. "
            "Run this adapter on the NVIDIA GPU machine after "
            "the local Qwen backend is configured."
        )

    def generate(self, prompt: str) -> str:
        """BaseModel-compatible generation interface."""
        raise NotImplementedError(
            "Qwen2.5-VL text generation is not connected yet."
        )