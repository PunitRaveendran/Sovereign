"""GPU VRAM monitoring for Sovereign model operations."""

import subprocess
from typing import Dict


class VRAMMonitor:
    """Monitor NVIDIA GPU memory usage."""

    def get_usage(self) -> Dict[str, int]:
        """Return GPU memory usage in MiB."""
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        total, used, free = result.stdout.strip().split(",")

        return {
            "total_mib": int(total.strip()),
            "used_mib": int(used.strip()),
            "free_mib": int(free.strip()),
        }

    def get_usage_percentage(self) -> float:
        """Return percentage of VRAM currently in use."""
        usage = self.get_usage()

        if usage["total_mib"] == 0:
            return 0.0

        return (usage["used_mib"] / usage["total_mib"]) * 100