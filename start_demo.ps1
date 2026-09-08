Write-Host "Starting Sovereign Demo Environment..."

Write-Host "1. Starting REAL llama-server with Flagship Models (Port 8080)..."
Start-Process -FilePath "powershell.exe" -ArgumentList "-ExecutionPolicy Bypass -File .\scripts\start_llama_server.ps1" -WindowStyle Normal

Write-Host "2. Starting Manoj's Microservices (Port 8001)..."
Start-Process -FilePath "..\.venv\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "manoj" -WindowStyle Hidden

Write-Host "Waiting for Manoj's API to become healthy..."
$healthy = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get -ErrorAction Stop
        if ($response.status -eq "ok") {
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $healthy) {
    Write-Error "Manoj's API failed to start on port 8001. Aborting."
    exit 1
}
Write-Host "Manoj's API is healthy!"

Write-Host "3. Starting Main Agent Core (Port 8000)..."
.\.venv\Scripts\python.exe -m app.main
