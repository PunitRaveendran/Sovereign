# prepare_wheels.ps1
# Run this on a CONNECTED machine to pre-download all pip wheels.
# Then copy the entire sovereign\manoj\ folder (including .\wheels\) to the
# air-gap laptop via USB drive.
#
# Usage:
#   cd sovereign\manoj
#   .\airgap\prepare_wheels.ps1

$WheelsDir = ".\wheels"

Write-Host "[*] Creating wheels directory: $WheelsDir"
New-Item -ItemType Directory -Force -Path $WheelsDir | Out-Null

Write-Host "[*] Downloading all wheels for requirements.txt..."
pip download -r requirements.txt -d $WheelsDir --prefer-binary

Write-Host "[*] Downloading pytest..."
pip download pytest -d $WheelsDir --prefer-binary

Write-Host ""
Write-Host "[+] Done. Wheels saved to $WheelsDir"
Write-Host "    Transfer the entire manoj\ folder to the air-gap machine via USB."
Write-Host "    Then run: .\airgap\install_offline.ps1"
