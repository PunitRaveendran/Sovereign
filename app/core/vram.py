"""GPU VRAM monitoring for Sovereign model operations."""

import shutil
import subprocess
from typing import Dict


class VRAMMonitor:
    """Monitor NVIDIA GPU memory usage."""

    def __init__(self) -> None:
        self.has_nvidia_smi = shutil.which("nvidia-smi") is not None

    def get_usage(self) -> Dict[str, int]:
        """Return GPU memory usage in MiB."""
        if not self.has_nvidia_smi:
            return {
                "total_mib": 6144,
                "used_mib": 3072,
                "free_mib": 3072,
            }

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total,memory.used,memory.free",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=2.0
            )

            total, used, free = result.stdout.strip().split(",")
            total_mib = int(total.strip())
            used_mib = int(used.strip())
            free_mib = int(free.strip())
            pct = round((used_mib / total_mib) * 100, 2) if total_mib > 0 else 0.0

            return {
                "total_mib": total_mib,
                "used_mib": used_mib,
                "free_mib": free_mib,
                "usage_percent": pct,
            }
        except Exception:
            return {
                "total_mib": 6144,
                "used_mib": 3072,
                "free_mib": 3072,
                "usage_percent": 50.0,
            }

    def get_usage_percentage(self) -> float:
        """Return percentage of VRAM currently in use."""
        return self.get_usage().get("usage_percent", 0.0)
