"""
network_monitor.py — Egress firewall setup guide + live network monitor backend.

Two responsibilities:
  1. Egress control: iptables/netns rules printed as a setup script
     (run once on the demo machine — Linux host or inside Docker).
  2. Live monitor: FastAPI endpoint that streams real-time packet counts
     and connection stats via SSE or polling.

Design notes:
  - The monitor is PURELY observational — it reads psutil counters, no
    raw-socket sniffing needed, so it works without root on Windows too.
  - "Packets out = 0" is the live sovereignty proof shown on the dashboard.
  - The firewall setup script is generated for Linux (Docker container or
    the air-gap laptop). On Windows the Docker --network none approach
    applies instead (see egress_rules() below).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import AsyncGenerator

import psutil
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from config import settings

# ══════════════════════════════════════════════════════════════════════════════
#  Egress firewall setup (Linux iptables / Docker)
# ══════════════════════════════════════════════════════════════════════════════

IPTABLES_SETUP_SCRIPT = """\
#!/bin/bash
# Sovereign — Egress firewall setup script
# Run as root on the demo machine (or inside a privileged container).
# Purpose: prove that the AI workbench makes ZERO external network calls.
#
# Strategy:
#   1. Allow established/related traffic so existing connections stay up.
#   2. Allow loopback (127.0.0.1) — all Sovereign services communicate locally.
#   3. Allow LAN only for intra-team traffic (optional — remove for full air-gap).
#   4. DROP everything else outbound.

set -euo pipefail

LOOPBACK="lo"
LAN_CIDR="192.168.0.0/16"     # adjust to your local subnet

echo "[*] Flushing existing OUTPUT rules..."
iptables -F OUTPUT

echo "[*] Allow loopback..."
iptables -A OUTPUT -o "$LOOPBACK" -j ACCEPT

echo "[*] Allow already-established connections..."
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

echo "[*] Allow LAN (optional — comment out for full air-gap)..."
iptables -A OUTPUT -d "$LAN_CIDR" -j ACCEPT

echo "[*] DROP everything else..."
iptables -A OUTPUT -j DROP

echo "[*] Current OUTPUT rules:"
iptables -L OUTPUT -v -n

echo "[+] Egress firewall active. All external traffic is blocked."
"""

DOCKER_COMPOSE_EGRESS = """\
# docker-compose.yml (excerpt) — enforce network isolation at container level
# Use --network none on the inference containers so even if iptables is wrong,
# Docker's own network namespace guarantees no egress path.

services:
  sovereign_api:
    image: sovereign:latest
    network_mode: none           # no network adapter at all
    volumes:
      - ./models:/models:ro
      - ./data:/data:ro
      - ./outputs:/outputs
    restart: unless-stopped

  # If you need the loopback dashboard, use a named network with internal: true
  sovereign_dashboard:
    image: sovereign_ui:latest
    networks:
      - internal_only
    ports:
      - "127.0.0.1:3000:3000"   # expose only on loopback, never 0.0.0.0

networks:
  internal_only:
    internal: true               # no routing to the host's external interface
"""


def print_egress_rules() -> None:
    """Print the iptables script and Docker compose excerpt to stdout."""
    print("=" * 70)
    print("SOVEREIGN — EGRESS FIREWALL SETUP")
    print("=" * 70)
    print("\n--- iptables script (save as setup_egress.sh, run as root) ---\n")
    print(IPTABLES_SETUP_SCRIPT)
    print("\n--- Docker Compose network isolation (excerpt) ---\n")
    print(DOCKER_COMPOSE_EGRESS)


def write_egress_scripts(output_dir: "Path | None" = None) -> None:
    """Write the egress control scripts to disk."""
    from pathlib import Path
    out = output_dir or (settings.base_dir / "egress")
    out.mkdir(parents=True, exist_ok=True)
    (out / "setup_egress.sh").write_text(IPTABLES_SETUP_SCRIPT, encoding="utf-8")
    (out / "docker-compose.egress.yml").write_text(DOCKER_COMPOSE_EGRESS, encoding="utf-8")
    logger.success("Egress scripts written to {}", out)


# ══════════════════════════════════════════════════════════════════════════════
#  Live network monitor
# ══════════════════════════════════════════════════════════════════════════════

class NetSnapshot:
    """Single point-in-time network counter snapshot."""

    def __init__(self) -> None:
        counters = psutil.net_io_counters(pernic=True)
        iface = settings.monitor_interface

        # Try the configured interface; fall back to aggregate
        if iface in counters:
            c = counters[iface]
        else:
            c = psutil.net_io_counters()

        self.ts           = time.monotonic()
        self.wall         = datetime.now(timezone.utc).isoformat()
        self.bytes_sent   = c.bytes_sent
        self.bytes_recv   = c.bytes_recv
        self.packets_sent = c.packets_sent
        self.packets_recv = c.packets_recv
        self.err_in       = c.errin
        self.err_out      = c.errout


class NetworkMonitor:
    """
    Polls psutil network counters and computes per-second deltas.
    The dashboard shows these values in real time.
    "Packets out = 0 during the entire demo" is the sovereignty proof.
    """

    def __init__(self, poll_interval: float = 1.0) -> None:
        self.poll_interval = poll_interval
        self._prev: NetSnapshot | None = None
        self._running = False
        self._latest: dict = {}

    def _compute_delta(self, prev: NetSnapshot, curr: NetSnapshot) -> dict:
        dt = max(curr.ts - prev.ts, 0.001)
        return {
            "ts":                    curr.wall,
            "interface":             settings.monitor_interface,
            "bytes_sent_per_sec":    round((curr.bytes_sent   - prev.bytes_sent)   / dt, 1),
            "bytes_recv_per_sec":    round((curr.bytes_recv   - prev.bytes_recv)   / dt, 1),
            "packets_sent_per_sec":  round((curr.packets_sent - prev.packets_sent) / dt, 1),
            "packets_recv_per_sec":  round((curr.packets_recv - prev.packets_recv) / dt, 1),
            "total_bytes_sent":      curr.bytes_sent,
            "total_bytes_recv":      curr.bytes_recv,
            "total_packets_sent":    curr.packets_sent,
            "total_packets_recv":    curr.packets_recv,
            "external_egress_alert": (curr.packets_sent - prev.packets_sent) > 0,
        }

    async def run(self) -> None:
        """Background polling loop — starts on app startup."""
        self._running = True
        self._prev = NetSnapshot()
        logger.info("Network monitor started (interface={})", settings.monitor_interface)
        while self._running:
            await asyncio.sleep(self.poll_interval)
            curr = NetSnapshot()
            self._latest = self._compute_delta(self._prev, curr)
            if self._latest.get("external_egress_alert"):
                logger.warning("⚠️  EGRESS ALERT: packets sent on {} at {}", settings.monitor_interface, curr.wall)
            self._prev = curr

    def stop(self) -> None:
        self._running = False

    def get_latest(self) -> dict:
        return self._latest or {
            "ts": datetime.now(timezone.utc).isoformat(),
            "interface": settings.monitor_interface,
            "bytes_sent_per_sec": 0, "bytes_recv_per_sec": 0,
            "packets_sent_per_sec": 0, "packets_recv_per_sec": 0,
            "total_bytes_sent": 0, "total_bytes_recv": 0,
            "total_packets_sent": 0, "total_packets_recv": 0,
            "external_egress_alert": False,
        }

    async def stream(self) -> AsyncGenerator[str, None]:
        """Server-Sent Events generator — consumed by the dashboard."""
        while self._running:
            data = json.dumps(self.get_latest())
            yield f"data: {data}\n\n"
            await asyncio.sleep(self.poll_interval)


# ══════════════════════════════════════════════════════════════════════════════
#  FastAPI app
# ══════════════════════════════════════════════════════════════════════════════

monitor = NetworkMonitor(poll_interval=settings.monitor_poll_interval)
app = FastAPI(title="Sovereign Network Monitor", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor.run())


@app.on_event("shutdown")
async def shutdown_event():
    monitor.stop()


@app.get("/network/stats")
async def api_stats():
    """Latest network stats snapshot — poll this from the dashboard."""
    return monitor.get_latest()


@app.get("/network/stream")
async def api_stream():
    """Server-Sent Events stream for real-time dashboard updates."""
    return StreamingResponse(
        monitor.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/network/interfaces")
async def api_interfaces():
    """List available network interfaces (helps configure the right one)."""
    counters = psutil.net_io_counters(pernic=True)
    return {
        "interfaces": list(counters.keys()),
        "configured": settings.monitor_interface,
    }


@app.get("/network/health")
async def health():
    return {"status": "ok", "monitoring": monitor._running}


@app.get("/network/egress-rules")
async def api_egress_rules():
    """Return the iptables + Docker firewall scripts as text."""
    return {
        "iptables_script":  IPTABLES_SETUP_SCRIPT,
        "docker_compose":   DOCKER_COMPOSE_EGRESS,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CLI entrypoint
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import uvicorn

    if len(sys.argv) > 1 and sys.argv[1] == "egress":
        write_egress_scripts()
    else:
        uvicorn.run("network_monitor:app", host=settings.api_host, port=8003, reload=False)
