#!/usr/bin/env bash
# ==============================================================================
# Sovereign AI Workbench — llama-server Startup Script (Linux / Aparna's Host)
# Port: 8080 (OpenAI-compatible /v1/chat/completions)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

MODEL_PATH="${1:-}"

# Check for llama-server binary
if command -v llama-server &> /dev/null; then
    LLAMA_BIN="llama-server"
elif [ -f "./llama-bin/llama-server" ]; then
    LLAMA_BIN="./llama-bin/llama-server"
else
    echo "[ERROR] llama-server not found in PATH or ./llama-bin/"
    echo "Install via: apt-get install llama.cpp or compile with cmake"
    exit 1
fi

# Model priority: Flagships first
if [ -z "$MODEL_PATH" ]; then
    FLAGSHIPS=(
        "$ROOT_DIR/models/granite-4.1-8b-instruct.Q4_K_M.gguf"
        "$ROOT_DIR/models/nemotron-nano-9b-instruct.Q4_K_M.gguf"
        "$ROOT_DIR/models/nemotron-nano-4b-instruct.Q4_K_M.gguf"
    )

    for candidate in "${FLAGSHIPS[@]}"; do
        if [ -f "$candidate" ]; then
            MODEL_PATH="$candidate"
            echo -e "\033[0;32m[MODEL SELECTED] Using Flagship Target: $(basename "$MODEL_PATH")\033[0m"
            break
        fi
    done

    if [ -z "$MODEL_PATH" ]; then
        FALLBACK="$ROOT_DIR/models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
        if [ -f "$FALLBACK" ]; then
            MODEL_PATH="$FALLBACK"
            echo -e "\033[1;33m=====================================================================\033[0m"
            echo -e "\033[1;33m[WARNING] Flagship target model (Granite/Nemotron) not found in models/.\033[0m"
            echo -e "\033[1;33m[FALLBACK] Defaulting to lightweight test stub: $(basename "$MODEL_PATH")\033[0m"
            echo -e "\033[1;33m[NOTE] Run 'python scripts/download_flagship_models.py' for full weights.\033[0m"
            echo -e "\033[1;33m=====================================================================\033[0m"
        else
            echo "[ERROR] No GGUF models found in ./models/"
            exit 1
        fi
    fi
fi

echo "Starting local llama-server on http://127.0.0.1:8080..."
echo "Binary: $LLAMA_BIN"
echo "Model:  $MODEL_PATH"

# If NVIDIA GPU present, use -ngl 999 to offload all layers to VRAM
GPU_ARGS=""
if command -v nvidia-smi &> /dev/null; then
    echo "[GPU DETECTED] Offloading layers to CUDA..."
    GPU_ARGS="-ngl 99"
fi

exec "$LLAMA_BIN" \
    -m "$MODEL_PATH" \
    --port 8080 \
    --host 127.0.0.1 \
    -c 4096 \
    $GPU_ARGS
