# build_usb_bundle.ps1
# Run this on the CONNECTED (hero) laptop to build a USB bundle
# that can set up the air-gap laptop with zero internet access.
#
# What it bundles:
#   1. All Python pip wheels (from requirements.txt)
#   2. The pre-built Chroma DB (so no re-ingestion needed on air-gap)
#   3. All source code and demo data
#   4. The egress firewall scripts
#
# Usage:
#   cd sovereign\manoj
#   .\airgap\build_usb_bundle.ps1 -OutputDir D:\SovereignUSB
#
# Then plug the USB into the air-gap laptop and run:
#   .\airgap\install_offline.ps1

param(
    [string]$OutputDir = ".\usb_bundle",
    [switch]$SkipWheels = $false
)

$ErrorActionPreference = "Stop"
$ManojDir = $PSScriptRoot | Split-Path -Parent

Write-Host ""
Write-Host "============================================================"
Write-Host "  SOVEREIGN — Building Air-Gap USB Bundle"
Write-Host "  Source:  $ManojDir"
Write-Host "  Output:  $OutputDir"
Write-Host "============================================================"
Write-Host ""

# Create output structure
$dirs = @(
    "$OutputDir\sovereign\manoj",
    "$OutputDir\sovereign\manoj\wheels",
    "$OutputDir\sovereign\manoj\egress",
    "$OutputDir\sovereign\manoj\airgap",
    "$OutputDir\sovereign\manoj\data",
    "$OutputDir\sovereign\manoj\chroma_db",
    "$OutputDir\sovereign\manoj\outputs",
    "$OutputDir\sovereign\manoj\tests"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

# ── Step 1: Copy source code ──────────────────────────────────────────────────
Write-Host "[1/4] Copying source code..."
$srcFiles = @(
    "config.py", "rbac.py", "ingestor.py", "kb_search.py",
    "doc_generator.py", "network_monitor.py", "main.py",
    "demo_data.py", "smoke_test.py", "models_manifest.yaml",
    "requirements.txt", ".env.example", "README.md"
)
foreach ($f in $srcFiles) {
    $src = Join-Path $ManojDir $f
    if (Test-Path $src) {
        Copy-Item $src "$OutputDir\sovereign\manoj\" -Force
        Write-Host "   copied: $f"
    }
}

# Copy subdirectories
foreach ($sub in @("airgap", "egress", "tests", "data")) {
    $srcDir = Join-Path $ManojDir $sub
    if (Test-Path $srcDir) {
        Copy-Item $srcDir "$OutputDir\sovereign\manoj\" -Recurse -Force
        Write-Host "   copied: $sub\"
    }
}
Write-Host "  [OK] Source code copied." -ForegroundColor Green

# ── Step 2: Copy Chroma DB ────────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/4] Copying Chroma vector DB (pre-built, no re-ingestion needed)..."
$chromaSrc = Join-Path $ManojDir "chroma_db"
if (Test-Path $chromaSrc) {
    Copy-Item $chromaSrc "$OutputDir\sovereign\manoj\" -Recurse -Force
    Write-Host "  [OK] Chroma DB copied." -ForegroundColor Green
} else {
    Write-Warning "  Chroma DB not found at $chromaSrc"
    Write-Warning "  Run: python demo_data.py --ingest   on the connected machine first."
}

# ── Step 3: Download pip wheels ────────────────────────────────────────────────
if (-not $SkipWheels) {
    Write-Host ""
    Write-Host "[3/4] Downloading pip wheels (this takes a few minutes)..."
    $wheelsDir = "$OutputDir\sovereign\manoj\wheels"
    pip download -r "$ManojDir\requirements.txt" -d $wheelsDir --prefer-binary -q
    pip download pytest -d $wheelsDir --prefer-binary -q
    $wheelCount = (Get-ChildItem $wheelsDir -Filter "*.whl").Count
    Write-Host "  [OK] $wheelCount wheels downloaded to $wheelsDir" -ForegroundColor Green
} else {
    Write-Host "[3/4] Skipping wheel download (-SkipWheels flag set)."
}

# ── Step 4: Write a README for the USB ────────────────────────────────────────
Write-Host ""
Write-Host "[4/4] Writing USB README..."
@"
SOVEREIGN — Air-Gap USB Bundle
================================

STEP 1: Copy this entire folder to the air-gap laptop (via USB).

STEP 2 (Windows air-gap laptop):
    cd sovereign\manoj
    .\airgap\install_offline.ps1

STEP 3 (Linux air-gap laptop):
    cd sovereign/manoj
    pip install -r requirements.txt --no-index --find-links ./wheels/
    sudo bash airgap/setup_airgap_linux.sh

STEP 4: Verify sovereignty:
    python airgap/airgap_verify.py
    -- All checks should PASS with Wi-Fi disabled at BIOS level.

STEP 5: Open Swagger UI:
    http://127.0.0.1:8001/docs

DEMO — RBAC proof (30 seconds):
    1. POST /kb/search  { role: "web_dev",  query: "vendor negotiation Q3" }
       -> empty result (executive doc blocked)
    2. POST /kb/search  { role: "vp_ceo",   query: "vendor negotiation Q3" }
       -> full answer grounded in executive_vendor_strategy_Q3.txt
    3. GET  /kb/audit   -> shows both attempts, denial logged

DEMO — Sovereignty proof:
    GET /network/stats  -> packets_sent_per_sec = 0 throughout
"@ | Set-Content "$OutputDir\README_USB.txt" -Encoding UTF8

Write-Host "  [OK] README written." -ForegroundColor Green

# ── Summary ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================"
$bundleSize = [math]::Round((Get-ChildItem $OutputDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Host "  Bundle complete: $OutputDir"
Write-Host "  Total size:      ~$bundleSize MB"
Write-Host ""
Write-Host "  Next: Copy $OutputDir to USB drive and carry to air-gap laptop."
Write-Host "============================================================"
