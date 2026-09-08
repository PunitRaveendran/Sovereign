from backend.app.model_ops.model_selector import ModelSelector


class FakeVRAMMonitor:
    """Fake VRAM monitor for testing."""

    def __init__(self, free_mib):
        self.free_mib = free_mib

    def get_usage(self):
        return {
            "total_mib": 8188,
            "used_mib": 8188 - self.free_mib,
            "free_mib": self.free_mib,
        }


def test_select_vision_model_when_vram_is_available():
    monitor = FakeVRAMMonitor(7000)
    selector = ModelSelector(vram_monitor=monitor)

    result = selector.select("vision")

    assert result["category"] == "vision"
    assert result["model_name"] == "qwen-vl"
    assert result["required_vram_mib"] == 6000
    assert result["available_vram_mib"] == 7000


def test_select_general_model():
    monitor = FakeVRAMMonitor(7000)
    selector = ModelSelector(vram_monitor=monitor)

    result = selector.select("general")

    assert result["model_name"] == "phi-4-mini"
    assert result["required_vram_mib"] == 3000


def test_can_run_returns_true_when_model_fits():
    monitor = FakeVRAMMonitor(7000)
    selector = ModelSelector(vram_monitor=monitor)

    assert selector.can_run("vision") is True


def test_can_run_returns_false_when_model_does_not_fit():
    monitor = FakeVRAMMonitor(5000)
    selector = ModelSelector(vram_monitor=monitor)

    assert selector.can_run("vision") is False


def test_select_rejects_model_when_vram_is_insufficient():
    monitor = FakeVRAMMonitor(5000)
    selector = ModelSelector(vram_monitor=monitor)

    try:
        selector.select("vision")
        assert False, "Expected RuntimeError"
    except RuntimeError as error:
        assert "Not enough VRAM" in str(error)


def test_get_required_vram():
    monitor = FakeVRAMMonitor(7000)
    selector = ModelSelector(vram_monitor=monitor)

    assert selector.get_required_vram("vision") == 6000
    assert selector.get_required_vram("coding") == 5000
    assert selector.get_required_vram("general") == 3000