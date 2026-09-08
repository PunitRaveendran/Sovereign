"""Controller for local Ollama models in Sovereign."""

import subprocess


class OllamaController:
    """Control local models through the Ollama CLI."""

    def __init__(self, ollama_command: str = "ollama") -> None:
        self.ollama_command = ollama_command

    def list_running_models(self) -> list[str]:
        """Return models currently loaded by Ollama."""
        result = subprocess.run(
            [self.ollama_command, "ps"],
            capture_output=True,
            text=True,
            check=True,
        )

        lines = result.stdout.strip().splitlines()

        if len(lines) <= 1:
            return []

        models = []

        for line in lines[1:]:
            parts = line.split()

            if parts:
                models.append(parts[0])

        return models

    def run_model(self, model_name: str, prompt: str) -> str:
        """Run a prompt using a local Ollama model."""
        result = subprocess.run(
            [
                self.ollama_command,
                "run",
                model_name,
                prompt,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    def stop_model(self, model_name: str) -> None:
        """Stop a running Ollama model."""
        subprocess.run(
            [
                self.ollama_command,
                "stop",
                model_name,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    def is_running(self, model_name: str) -> bool:
        """Check whether a specific model is running."""
        return model_name in self.list_running_models()