# ==============================================================================
# Sovereign AI Workbench — llama-server Startup Script (Windows)
# Port: 8080 (OpenAI-compatible /v1/chat/completions)
# ==============================================================================

param (
    [string]$ModelPath = ""
)

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RootDir

$Binary = "$RootDir\llama-bin-gpu\llama-server.exe"
if (-not (Test-Path $Binary)) {
    $Binary = "$RootDir\llama-bin-cpu\llama-server.exe"
}
if (-not (Test-Path $Binary)) {
    $Binary = "$RootDir\llama-bin\llama-server.exe"
}

if (-not (Test-Path $Binary)) {
    Write-Error "Could not find llama-server.exe in llama-bin-gpu, llama-bin-cpu, or llama-bin."
    exit 1
}

# Resolve Model: Prioritize Flagships over test stub
if ([string]::IsNullOrEmpty($ModelPath)) {
    $FlagshipList = @(
        "$RootDir\models\nemotron-nano-4b-instruct.Q4_K_M.gguf",
        "$RootDir\models\granite-4.1-8b-instruct.Q4_K_M.gguf",
        "$RootDir\models\nemotron-nano-9b-instruct.Q4_K_M.gguf"
    )

    foreach ($Candidate in $FlagshipList) {
        if (Test-Path $Candidate) {
            $ModelPath = $Candidate
            Write-Host "[MODEL SELECTED] Using Flagship Target: $(Split-Path -Leaf $ModelPath)" -ForegroundColor Green
            break
        }
    }

    if ([string]::IsNullOrEmpty($ModelPath)) {
        $FallbackStub = "$RootDir\models\qwen2.5-0.5b-instruct-q4_k_m.gguf"
        if (Test-Path $FallbackStub) {
            $ModelPath = $FallbackStub
            Write-Host "=====================================================================" -ForegroundColor Yellow
            Write-Host "[WARNING] Flagship target model (Granite/Nemotron) not found in models/." -ForegroundColor Yellow
            Write-Host "[FALLBACK] Defaulting to lightweight test stub: $(Split-Path -Leaf $ModelPath)" -ForegroundColor Yellow
            Write-Host "[NOTE] Run 'python scripts\download_flagship_models.py' for full demo weights." -ForegroundColor Yellow
            Write-Host "=====================================================================" -ForegroundColor Yellow
        } else {
            Write-Error "No GGUF model files found in $RootDir\models\. Aborting."
            exit 1
        }
    }
}

Write-Host "Starting llama-server on http://127.0.0.1:8080 (RTX GPU ACCELERATED)..." -ForegroundColor Cyan
Write-Host "Binary: $Binary"
Write-Host "Model:  $ModelPath"

& $Binary `
    -m "$ModelPath" `
    --port 8080 `
    --host 127.0.0.1 `
    -c 4096 `
    -ngl 99 `
    -rea off `
    --no-jinja `
    --chat-template chatml
