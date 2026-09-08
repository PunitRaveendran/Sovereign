# Create models directory
New-Item -ItemType Directory -Force -Path "models"

# 1. Download llama-server.exe
Write-Host "Fetching latest llama.cpp release..."
$releases = Invoke-RestMethod -Uri "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
$asset = $releases.assets | Where-Object { $_.name -match "llama-b\d+-bin-win-vulkan-x64\.zip" }
if (-not $asset) {
    Write-Host "Could not find vulcan asset. Falling back to prebuilt cpu..."
    $asset = $releases.assets | Where-Object { $_.name -match "llama-b\d+-bin-win-avx2-x64\.zip" }
}

Write-Host "Downloading $($asset.name)..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile "llama-server.zip"
Write-Host "Extracting..."
Expand-Archive -Path "llama-server.zip" -DestinationPath "llama-bin" -Force
Remove-Item "llama-server.zip"

# 2. Download Qwen2.5-0.5B-Instruct-Q4_K_M.gguf
Write-Host "Downloading Qwen2.5-0.5B test model (~390MB)..."
$modelUrl = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true"
Invoke-WebRequest -Uri $modelUrl -OutFile "models\qwen2.5-0.5b-instruct-q4_k_m.gguf"
Write-Host "Download complete!"
