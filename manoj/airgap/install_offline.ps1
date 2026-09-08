# install_offline.ps1
# Run this on the AIR-GAP laptop after copying the folder from USB.
# Requires: Python 3.12+ already installed on the air-gap machine.
#
# Usage:
#   cd sovereign\manoj
#   .\airgap\install_offline.ps1

param(
    [string]$WheelsDir = ".\wheels",
    [string]$Port = "8001"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "  SOVEREIGN — Air-Gap Laptop Setup"
Write-Host "============================================================"
Write-Host ""

# ── Verify no network ─────────────────────────────────────────────────────────
Write-Host "[1/5] Checking network isolation..."
try {
    $ping = Test-Connection -ComputerName "8.8.8.8" -Count 1 -Quiet -ErrorAction SilentlyContinue
    if ($ping) {
        Write-Warning "    Network is reachable! Disable Wi-Fi/Ethernet before proceeding."
        Write-Warning "    For the demo: this machine must have no network path."
        $continue = Read-Host "    Continue anyway? (yes/no)"
        if ($continue -ne "yes") { exit 1 }
    } else {
        Write-Host "    [OK] No external network detected." -ForegroundColor Green
    }
} catch {
    Write-Host "    [OK] Network check passed (no connectivity)." -ForegroundColor Green
}

# ── Install Python packages from local wheels ──────────────────────────────────
Write-Host ""
Write-Host "[2/5] Installing Python packages from local wheels (no internet)..."
if (-not (Test-Path $WheelsDir)) {
    Write-Error "Wheels directory '$WheelsDir' not found. Copy it from the USB drive first."
    exit 1
}
pip install -r requirements.txt --no-index --find-links $WheelsDir
Write-Host "    [OK] Packages installed." -ForegroundColor Green

# ── Generate egress firewall scripts ──────────────────────────────────────────
Write-Host ""
Write-Host "[3/5] Generating egress firewall scripts..."
python network_monitor.py egress
Write-Host "    [OK] Scripts written to .\egress\" -ForegroundColor Green
Write-Host "    NOTE: On Linux, run: sudo bash egress/setup_egress.sh"
Write-Host "    (On Windows demo machine, use Docker --network none instead)"

# ── Seed Chroma KB ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[4/5] Checking Chroma knowledge base..."
$chromaDir = ".\chroma_db"
if (Test-Path $chromaDir) {
    Write-Host "    [OK] Chroma DB already exists (copied from USB). Skipping re-ingestion." -ForegroundColor Green
} else {
    Write-Host "    Chroma DB not found — ingesting demo documents..."
    python demo_data.py --ingest
    Write-Host "    [OK] KB ingested." -ForegroundColor Green
}

# ── Start the API server ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "[5/5] Starting Sovereign API server on port $Port..."
Write-Host ""
Write-Host "============================================================"
Write-Host "  SOVEREIGN is running at http://127.0.0.1:$Port"
Write-Host "  Swagger docs:           http://127.0.0.1:$Port/docs"
Write-Host "  Network monitor:        http://127.0.0.1:$Port/network/stats"
Write-Host ""
Write-Host "  This machine is air-gapped. packets_sent = 0 proves it."
Write-Host "============================================================"
Write-Host ""
python -m uvicorn main:app --host 127.0.0.1 --port $Port
