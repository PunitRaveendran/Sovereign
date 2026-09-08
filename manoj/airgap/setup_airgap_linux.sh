#!/bin/bash
# setup_airgap_linux.sh
# Run this on the air-gap laptop (Linux) as root.
# Assumes Python packages are already installed (via install_offline.ps1 or pip offline).
#
# Usage:
#   sudo bash airgap/setup_airgap_linux.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANOJ_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "  SOVEREIGN — Air-Gap Linux Setup"
echo "============================================================"
echo ""

# ── Verify no network ─────────────────────────────────────────────────────────
echo "[1/4] Verifying network isolation..."
if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
    echo "  WARNING: External network is reachable!"
    echo "  Disable Wi-Fi in BIOS and unplug Ethernet before proceeding."
    read -rp "  Continue anyway? (yes/no): " ans
    [[ "$ans" != "yes" ]] && exit 1
else
    echo "  [OK] No external network detected."
fi

# ── Apply iptables egress rules ───────────────────────────────────────────────
echo ""
echo "[2/4] Applying iptables egress firewall..."
EGRESS_SCRIPT="$MANOJ_DIR/egress/setup_egress.sh"

if [[ ! -f "$EGRESS_SCRIPT" ]]; then
    echo "  Generating egress scripts first..."
    cd "$MANOJ_DIR"
    python network_monitor.py egress
fi

bash "$EGRESS_SCRIPT"
echo "  [OK] Firewall active. Verifying..."

# Show current OUTPUT chain
echo ""
echo "  Current iptables OUTPUT rules:"
iptables -L OUTPUT -v -n --line-numbers
echo ""

# Confirm external traffic is blocked
if curl --max-time 3 https://google.com &>/dev/null; then
    echo "  ERROR: External traffic still reachable. Check iptables rules."
    exit 1
else
    echo "  [OK] External traffic blocked (curl to google.com failed as expected)."
fi

# ── Seed Chroma KB ────────────────────────────────────────────────────────────
echo ""
echo "[3/4] Checking Chroma knowledge base..."
cd "$MANOJ_DIR"
if [[ -d "chroma_db" && "$(ls -A chroma_db)" ]]; then
    echo "  [OK] Chroma DB exists (copied from USB). Skipping re-ingestion."
else
    echo "  Ingesting demo documents..."
    python demo_data.py --ingest
    echo "  [OK] KB ingested."
fi

# ── Start the server ──────────────────────────────────────────────────────────
echo ""
echo "[4/4] Starting Sovereign API..."
echo ""
echo "============================================================"
echo "  SOVEREIGN running at http://127.0.0.1:8001"
echo "  Docs: http://127.0.0.1:8001/docs"
echo ""
echo "  AIR-GAP PROOF:"
echo "  - Wi-Fi/BT disabled at BIOS level"
echo "  - iptables OUTPUT chain drops all non-loopback traffic"
echo "  - Docker containers use --network none"
echo "  - Network monitor at /network/stats shows packets_sent=0"
echo "============================================================"
echo ""
cd "$MANOJ_DIR"
python -m uvicorn main:app --host 127.0.0.1 --port 8001
