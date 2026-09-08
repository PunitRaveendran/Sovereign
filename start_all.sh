#!/usr/bin/env bash
# ==============================================================================
# Sovereign AI Workbench — Master Stack Orchestrator (Linux / Aparna's Host)
# Launches:
#   1. LLM Engine (Port 8080) — Real GGUF via llama-server
#   2. Manoj's Microservices (Port 8001) — Chroma KB, Office DocGen, Sandbox
#   3. Punit's Agent Core (Port 8000) — LangGraph Brain, Lateral RBAC, Audit Hash Chain
# ==============================================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo -e "\033[0;36m=================================================================\033[0m"
echo -e "\033[0;36m         SOVEREIGN AI WORKBENCH — STARTING SYSTEM STACK          \033[0m"
echo -e "\033[0;36m Mode: ${MODE^^} | Root: $ROOT_DIR\033[0m"
echo -e "\033[0;36m=================================================================\033[0m"

PIDS=()

cleanup() {
    echo -e "\n\033[0;33m[SHUTDOWN] Stopping background services...\033[0m"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start Real LLM Engine
echo -e "\n\033[0;32m[1/3] Launching REAL llama-server on port 8080...\033[0m"
./scripts/start_llama_server.sh &
PIDS+=($!)

# 2. Start Manoj's Microservices
echo -e "\n\033[0;32m[2/3] Launching Manoj's Microservices on port 8001...\033[0m"
(cd manoj && python -m uvicorn main:app --host 127.0.0.1 --port 8001) &
PIDS+=($!)

# Wait for services to become healthy
echo -e "\n\033[0;33m[WAIT] Waiting for background services to report healthy...\033[0m"
for i in {1..15}; do
    sleep 2
    if curl -s http://127.0.0.1:8001/health > /dev/null 2>&1; then
        echo -e "\033[0;32m  -> Microservices (8001): ONLINE\033[0m"
        break
    fi
done

# 3. Start Agent Core
echo -e "\n\033[0;36m[3/3] Starting Sovereign Agent Core on port 8000...\033[0m"
echo -e "\033[0;36m=================================================================\033[0m"
echo -e " Swagger Docs:  http://127.0.0.1:8000/docs"
echo -e " Manoj Docs:    http://127.0.0.1:8001/docs"
echo -e " Press Ctrl+C to terminate all services."
echo -e "\033[0;36m=================================================================\n\033[0m"

python -m app.main
