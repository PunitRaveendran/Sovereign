"""
download_flagship_models.py — Pulls real quantized GGUF models for Sovereign
Sources models directly from Hugging Face for local offline execution.
"""

import os
import sys
import argparse
import requests
from pathlib import Path

MODEL_REGISTRY = {
    "granite-8b": {
        "filename": "granite-4.1-8b-instruct.Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/granite-3.1-8b-instruct-GGUF/resolve/main/granite-3.1-8b-instruct-Q4_K_M.gguf",
        "size_gb": 4.9,
        "description": "IBM Granite 8B Instruct (Enterprise coding & tool-use)"
    },
    "nemotron-4b": {
        "filename": "nemotron-nano-4b-instruct.Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/nvidia_Llama-3.1-Nemotron-Nano-4B-v1.1-GGUF/resolve/main/nvidia_Llama-3.1-Nemotron-Nano-4B-v1.1-Q4_K_M.gguf",
        "size_gb": 2.7,
        "description": "NVIDIA Nemotron 4B Instruct (Compact, low-VRAM reasoning)"
    },
    "qwen-coder-7b": {
        "filename": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "size_gb": 4.68,
        "description": "Qwen 2.5 Coder 7B Instruct (State-of-the-art coding)"
    },
    "qwen-0.5b": {
        "filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "size_gb": 0.49,
        "description": "Qwen 2.5 0.5B Instruct (Ultra-lightweight test model)"
    }
}

def download_model(model_key: str, dest_dir: Path):
    if model_key not in MODEL_REGISTRY:
        print(f"Error: Unknown model '{model_key}'. Available: {list(MODEL_REGISTRY.keys())}")
        sys.exit(1)

    info = MODEL_REGISTRY[model_key]
    dest_path = dest_dir / info["filename"]
    dest_dir.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        print(f"[FOUND] {info['filename']} already exists ({size_mb:.1f} MB). Skipping download.")
        return dest_path

    print(f"\n[DOWNLOADING] {info['description']}")
    print(f"Target: {dest_path}")
    print(f"Estimated Size: {info['size_gb']} GB")
    print(f"URL: {info['url']}\n")

    try:
        with requests.get(info["url"], stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024 * 2 # 2MB chunks

            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = (downloaded / total_size) * 100
                            mb = downloaded / (1024 * 1024)
                            tot_mb = total_size / (1024 * 1024)
                            print(f"\rProgress: {mb:.1f}/{tot_mb:.1f} MB ({pct:.1f}%)", end="", flush=True)

        print("\n[COMPLETE] Model downloaded successfully.")
        return dest_path
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        print(f"\n[ERROR] Download failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download GGUF flagship models for Sovereign")
    parser.add_argument("--model", default="granite-8b", choices=list(MODEL_REGISTRY.keys()),
                        help="Model key to download (default: granite-8b)")
    parser.add_argument("--dest", default="./models", help="Destination directory (default: ./models)")
    args = parser.parse_args()

    download_model(args.model, Path(args.dest))
