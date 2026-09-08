"""Task Service Module.

Connects task routing with model selection, model lifecycle management,
model inference, and multimodal processing.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from backend.app.model_ops.model_orchestrator import ModelOrchestrator
from backend.app.router.task_router import classify_task
from backend.app.multimodal.pipeline import MultimodalPipeline


def process_task(
    prompt: str,
    config_path: Optional[Union[str, Path]] = None,
    file_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Process a user request end-to-end.

    Args:
        prompt: The user's request.
        config_path: Optional custom models.yaml path.
        file_path: Optional image or PDF file.

    Returns:
        Dictionary containing the task result.
    """

    service = TaskService(config_path=config_path)

    return service.execute(
        prompt=prompt,
        file_path=file_path,
    )


class TaskService:
    """Service for end-to-end task routing and model execution."""

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        orchestrator: Optional[ModelOrchestrator] = None,
        multimodal_pipeline: Optional[MultimodalPipeline] = None,
    ) -> None:
        """Initialize the task service."""

        self.config_path = config_path

        if orchestrator is not None:
            self.orchestrator = orchestrator
        else:
            self.orchestrator = ModelOrchestrator()

        if multimodal_pipeline is not None:
            self.multimodal_pipeline = multimodal_pipeline
        else:
            self.multimodal_pipeline = MultimodalPipeline()

    def execute(
        self,
        prompt: str,
        file_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Process a text-only or multimodal request."""

        # ---------------------------------------------------------
        # Step 1: Classify the request
        # ---------------------------------------------------------
        category = classify_task(prompt)

        # ---------------------------------------------------------
        # Step 2: Process attached file if one exists
        # ---------------------------------------------------------
        multimodal_result = None

        if file_path is not None:
            multimodal_result = self.multimodal_pipeline.process(
                file_path=str(file_path),
                prompt=prompt,
            )

        # ---------------------------------------------------------
        # Step 3: Prepare the appropriate model
        # ---------------------------------------------------------
        selection = self.orchestrator.prepare_model(category)

        model_name = selection["model_name"]
        backend = selection["backend"]

        # ---------------------------------------------------------
        # Step 4: Get the active model
        # ---------------------------------------------------------
        model = self.orchestrator.manager.get_active_model()

        # ---------------------------------------------------------
        # Step 5: Build the model prompt
        # ---------------------------------------------------------
        model_prompt = prompt

        if multimodal_result is not None:
            extracted_text = multimodal_result.get("text")

            if extracted_text:
                model_prompt = (
                    f"{prompt}\n\n"
                    f"Content extracted from the attached file:\n"
                    f"{extracted_text}"
                )

        # ---------------------------------------------------------
        # Step 6: Generate the response
        # ---------------------------------------------------------
        response_text = model.generate(model_prompt)

        # ---------------------------------------------------------
        # Step 7: Return the result
        # ---------------------------------------------------------
        result = {
            "category": category,
            "response": response_text,
            "model_name": model_name,
            "backend": backend,
        }

        if multimodal_result is not None:
            result["multimodal"] = multimodal_result

        return result