# ==============================================================================
# Sovereign AI Workbench — Master Stack Orchestrator (Windows)
# Launches:
#   1. LLM Engine (Port 8080) — Real GGUF via llama-server
#   2. Manoj's Microservices (Port 8001) — Chroma KB, Office DocGen, Sandbox
#   3. Punit's Agent Core (Port 8000) — LangGraph Brain, Lateral RBAC, Audit Hash Chain
# ==============================================================================

param (
    [string]$ModelPath = ""
)

$ErrorActionPreference = "Stop"
$RootDir = $PSScriptRoot
Set-Location $RootDir

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "         SOVEREIGN AI WORKBENCH — STARTING SYSTEM STACK          " -ForegroundColor Cyan
Write-Host " REAL GGUF INFERENCE | Root: $RootDir" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Start Real LLM Engine
Write-Host "`n[1/3] Launching REAL llama-server (Port 8080)..." -ForegroundColor Green
$LlamaScript = "$RootDir\scripts\start_llama_server.ps1"
if (-not [string]::IsNullOrEmpty($ModelPath)) {
    Start-Process -FilePath "powershell.exe" -ArgumentList "-ExecutionPolicy Bypass -File `"$LlamaScript`" -ModelPath `"$ModelPath`"" -WindowStyle Normal
} else {
    Start-Process -FilePath "powershell.exe" -ArgumentList "-ExecutionPolicy Bypass -File `"$LlamaScript`"" -WindowStyle Normal
}

# 2. Start Manoj's Microservices
Write-Host "`n[2/3] Launching Manoj's Microservices (Port 8001)..." -ForegroundColor Green
Start-Process -FilePath "..\.venv\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "manoj" -WindowStyle Hidden

# Health Check Waiting Loop
Write-Host "`n[WAIT] Waiting for background microservices to turn healthy..." -ForegroundColor DarkYellow
$Healthy8001 = $false
$Healthy8080 = $false

for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 2
    
    # Check 8001
    if (-not $Healthy8001) {
        try {
            $resp8001 = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp8001.status -eq "ok") {
                $Healthy8001 = $true
                Write-Host "  -> Microservices (8001): ONLINE (Sandbox Backend: $($resp8001.sandbox_backend))" -ForegroundColor Green
            }
        } catch {}
    }

    # Check 8080
    if (-not $Healthy8080) {
        try {
            $body = '{"model":"local-model","messages":[{"role":"user","content":"test"}]}'
            $resp8080 = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/chat/completions" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp8080) {
                $Healthy8080 = $true
                Write-Host "  -> LLM Engine (8080):    ONLINE" -ForegroundColor Green
            }
        } catch {}
    }

    if ($Healthy8001 -and $Healthy8080) {
        break
    }
}

if (-not $Healthy8001) {
    Write-Host "  [WARN] Port 8001 not responding yet. Proceeding with launch..." -ForegroundColor Yellow
}
if (-not $Healthy8080) {
    Write-Host "  [WARN] Port 8080 not responding yet. Proceeding with launch..." -ForegroundColor Yellow
}

# 3. Start Main Agent Core (Foreground)
Write-Host "`n[3/3] Starting Sovereign Agent Core (Port 8000)..." -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Swagger Docs:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host " Manoj Docs:    http://127.0.0.1:8001/docs" -ForegroundColor White
Write-Host " Press Ctrl+C in this terminal to stop the Agent Core." -ForegroundColor DarkGray
Write-Host "=================================================================`n" -ForegroundColor Cyan

.\.venv\Scripts\python.exe -m app.main
