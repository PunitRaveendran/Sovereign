import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.models.base import BaseModel
from backend.app.models.local_llm import LocalLLM
from backend.app.models.mock import MockModel
from backend.app.models.registry import (
    get_model_config,
    get_model_for_category,
    load_model_configs,
)
from backend.app.multimodal.vision import QwenVisionModel


def test_load_model_configs():
    configs = load_model_configs()

    assert isinstance(configs, dict)
    assert "coding" in configs
    assert "vision" in configs
    assert "document" in configs
    assert "general" in configs


def test_category_configurations():
    coding = get_model_config("coding")
    assert coding["model_name"] == "granite"
    assert coding["backend"] == "llama.cpp"

    vision = get_model_config("vision")
    assert vision["model_name"] == "qwen-vl"
    assert vision["backend"] == "llama.cpp"

    document = get_model_config("document")
    assert document["model_name"] == "nemotron"
    assert document["backend"] == "llama.cpp"

    general = get_model_config("general")
    assert general["model_name"] == "phi-4-mini"
    assert general["backend"] == "llama.cpp"


def test_mock_model_generation():
    model = MockModel(
        model_name="test-llm",
        backend="llama.cpp",
    )

    assert isinstance(model, BaseModel)

    prompt = "Write a function to sort a list."

    response = model.generate(prompt)

    assert isinstance(response, str)
    assert "test-llm" in response
    assert "llama.cpp" in response
    assert prompt in response


def test_get_model_for_category():
    coding_model = get_model_for_category("coding")

    assert isinstance(coding_model, BaseModel)
    assert isinstance(coding_model, MockModel)
    assert coding_model.model_name == "granite"
    assert coding_model.backend == "llama.cpp"

    vision_model = get_model_for_category("vision")

    assert isinstance(vision_model, BaseModel)
    assert isinstance(vision_model, QwenVisionModel)
    assert vision_model.model_name == "qwen-vl"
    assert vision_model.backend == "llama.cpp"

    document_model = get_model_for_category("document")

    assert isinstance(document_model, BaseModel)
    assert isinstance(document_model, MockModel)
    assert document_model.model_name == "nemotron"
    assert document_model.backend == "llama.cpp"

    general_model = get_model_for_category("general")

    assert isinstance(general_model, BaseModel)
    assert isinstance(general_model, MockModel)
    assert general_model.model_name == "phi-4-mini"
    assert general_model.backend == "llama.cpp"


def test_fallback_category():
    config = get_model_config("unrecognized_category")

    assert config["model_name"] == "phi-4-mini"
    assert config["backend"] == "llama.cpp"


def test_local_llm_structure():
    llm = LocalLLM(
        model_name="granite",
        backend="llama.cpp",
        config={"temperature": 0.2},
    )

    assert isinstance(llm, BaseModel)
    assert llm.model_name == "granite"
    assert llm.backend == "llama.cpp"
    assert llm.config == {"temperature": 0.2}