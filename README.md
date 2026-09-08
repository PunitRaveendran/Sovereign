# Sovereign — Air-Gapped Industrial AI Workbench

> **A self-hosted, sovereign AI workbench for high-stakes industrial operations.**  
> Runs 100% on-device on consumer RTX laptop GPUs, automatically routes tasks across a heterogeneous open-weight model stack, enforces strict data-layer RBAC, executes sandboxed code with zero network egress, generates real enterprise deliverables, and cryptographically proves every action in a tamper-evident audit ledger.

---

## 📑 Table of Contents
1. [Core Features](#-core-features)
2. [Heterogeneous Model Stack](#-heterogeneous-model-stack)
3. [System Architecture](#-system-architecture)
4. [Hardware & Software Prerequisites](#-hardware--software-prerequisites)
5. [Quick Start & How to Run](#-quick-start--how-to-run)
6. [Automated Verification & Diagnostics Suite](#-automated-verification--diagnostics-suite)
7. [API Reference](#-api-reference)
8. [Live Demo Walkthrough for Evaluators](#-live-demo-walkthrough-for-evaluators)
9. [Project Layout & Directory Structure](#-project-layout--directory-structure)

---

## ⚡ Core Features

* **Real Agentic Loop (LangGraph)**: Operates a true **Plan → Act → Observe → Critique** state machine. The agent breaks down high-level industrial instructions, invokes local tools, inspects tool outputs, and self-corrects before finalizing output.
* **Data-Layer Role-Based Access Control (RBAC)**: Security is enforced at the database retrieval and tool gatekeeper level—**never by relying on prompt instructions**. Restricted users physically cannot retrieve or invoke restricted documents or tools.
* **Cryptographic Tamper-Evident Audit Ledger**: Every prompt, tool execution, RBAC check, and document generation is hashed into a local, append-only **SHA-256 Merkle chain** (`audit_log.jsonl`). Any attempt to alter historical logs invalidates the cryptographic root hash.
* **Multimodal Document Understanding & Grounding**: Upload scanned inspection reports, engineering drawings, or equipment photos. The system processes them on-device via neural vision models and **RapidOCR**, extracts actual numerical measurements, and directly grounds them in enterprise deliverables (`.docx`, `.pptx`, `.xlsx`).
* **Anti-Hallucination Self-Critique**: If an uploaded scan is blank, ambiguous, or lacks valid machine-readable telemetry, the self-critique module flags a `⚠️ [LOW CONFIDENCE - VERIFY BEFORE USE]` banner and refuses to fabricate fake numbers.
* **Zero-Egress Isolated Code Sandbox**: Executes Python calculations (e.g., pump head loss, hydraulic efficiency, 800×800 matrix operations) in an isolated container/subprocess with a **1GB memory ceiling** and socket networking blocked at the kernel level.
* **Hardware-Level Proof of Sovereignty**: Real-time network monitor tracks packet egress, demonstrating that 0 bytes leave the machine during inference and document creation.

---

## 🧠 Heterogeneous Model Stack

Sovereign avoids defaulting to a single model family. Each model is chosen for specific silicon and task performance:

| Task / Domain | Model | Why This Model | Precision | VRAM Footprint |
| :--- | :--- | :--- | :---: | :---: |
| **Agent Core & Reasoning** | **NVIDIA Nemotron 3 Nano (4B / 9B)** | Hybrid Mamba-Transformer architecture tuned for RTX silicon, low hallucination, and accurate JSON tool-calling. | Q4_K_M | ~3.2 GB – 5.5 GB |
| **Code Execution & Math** | **IBM Granite 4.1 8B Instruct** | Apache-licensed, exceptional benchmarks on code synthesis and tool orchestration. | Q4_K_M | ~4.8 GB |
| **Visual Inspection & Scans** | **Qwen2.5-VL-7B-Instruct** | Best-in-class open vision-language model for engineering drawings and document layouts. | Q4_K_M | ~5.8 GB |
| **On-Device Optical OCR** | **RapidOCR (PP-OCRv4 ONNX)** | Pure on-device neural text/number recognition. Zero cloud APIs, zero external binary installers. | ONNX fp32 | CPU / ~200 MB |
| **Semantic RAG Embeddings** | **BAAI/bge-small-en-v1.5** | Fast, high-density vector representation for local industrial SOPs and technical manuals. | fp16 | < 800 MB |

*Models are served locally via an optimized `llama-server` engine compiled with AVX2 and NVIDIA CUDA 12 support.*

---

## 🏗 System Architecture

```
                               ┌────────────────────────────────────────┐
                               │       Client / Evaluator Terminal      │
                               └───────────────────┬────────────────────┘
                                                   │ HTTP / REST
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Sovereign AI Workbench — Port 8000 (app.main:app)                                                │
│                                                                                                  │
│   ┌───────────────────────────┐    ┌─────────────────────────────────────────────────────────┐   │
│   │ Neural Task Classifier    │    │ LangGraph Agent Core                                    │   │
│   │ (Routes to Granite/Nemo)  │    │  [Plan] ──► [Act] ──► [Observe] ──► [Critique]          │   │
│   └─────────────┬─────────────┘    └────────────────────────────┬────────────────────────────┘   │
│                 │                                               │                                │
│   ┌─────────────┴─────────────┐                                 │ Calls Tools via RBAC Gate      │
│   │ Multimodal Ingestion      │                                 ▼                                │
│   │ RapidOCR + Qwen Vision    │                    ┌─────────────────────────┐                   │
│   └───────────────────────────┘                    │ Lateral RBAC Gatekeeper │                   │
│                                                    └────────────┬────────────┘                   │
└─────────────────────────────────────────────────────────────────┼────────────────────────────────┘
                                                                  │
                    ┌─────────────────────────────────────────────┴──────────────────┐
                    ▼                                                                ▼
┌──────────────────────────────────────┐                         ┌──────────────────────────────────────┐
│ Port 8001: Manoj Microservices       │                         │ Port 8080: Local Inference Engine    │
│  - Chroma Vector DB (Indexed RAG)    │                         │  - llama-server.exe (CUDA Offload)   │
│  - Document Generator (DOCX/PPTX)    │                         │  - ~65 tokens/sec on RTX 4050 GPU    │
│  - Hardened Code Sandbox (1GB limit) │                         │  - OpenAI-compatible `/v1/*` endpoint │
│  - Live Network Telemetry Monitor    │                         └──────────────────────────────────────┘
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Cryptographic Data Layer: audit_log.jsonl (SHA-256 Merkle Chain)                                │
│  [Record N-1 Hash] ──► [Event Data + User ID + Role + Result] ──► [Record N Hash]               │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 💻 Hardware & Software Prerequisites

* **Operating System**: Windows 11 (64-bit) or Linux (Ubuntu 22.04+).
* **GPU**: NVIDIA RTX Laptop GPU (e.g., RTX 3060, 4050, 4060, 5050 with 6GB–8GB VRAM) or CPU-only mode.
* **Python**: Python 3.11 or 3.12.
* **Disk Space**: ~10GB for quantized model weights and vector embeddings.

---

## 🚀 Quick Start & How to Run

### 1. Environment Setup

Clone or extract the project to your workspace:
```powershell
cd "c:\Users\Punit Raveendran\Desktop\SIH"

# Create and activate the Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install core dependencies
pip install -r requirements.txt
pip install rapidocr-onnxruntime opencv-python docx pymupdf
```

### 2. Launching All Services

You can launch the entire stack with a single command using the automated orchestrator:

#### On Windows (PowerShell):
```powershell
# Live Mode with real GPU model serving:
.\start_all.ps1 -Mode real

# Or Mock/Fast Mode for rapid test iterations without GPU overhead:
.\start_all.ps1 -Mode mock
```

#### On Linux (Bash):
```bash
chmod +x start_all.sh scripts/*.sh
./start_all.sh real
```

#### Manual Independent Startup (3 Separate Terminals):
If you prefer running services in dedicated terminals for live log monitoring:

* **Terminal 1 — LLM Engine (Port 8080)**:
  ```powershell
  .\scripts\start_llama_server.ps1
  ```
* **Terminal 2 — Microservices Gateway (Port 8001)**:
  ```powershell
  cd manoj
  ..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
  ```
* **Terminal 3 — Sovereign Agent Core & Gateway (Port 8000)**:
  ```powershell
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```

---

## 🧪 Automated Verification & Diagnostics Suite

The repository contains five dedicated diagnostic test scripts to verify full system integrity:

### 1. Full System Health Diagnostic (All 4 Pillars)
Verifies local LLM inference, Manoj's microservices, Punit's Agent Core, and cryptographic audit hashing:
```powershell
.\.venv\Scripts\python.exe verify_full_stack.py
```
*Expected Output:*
```text
====================================================================
                      DIAGNOSTIC SUMMARY
====================================================================
  1. LLM Serving Engine (:8080):       [PASS]
  2. Manoj's Microservices (:8001):     [PASS]
  3. Punit's Agent Core (:8000):        [PASS]
  4. Cryptographic Audit Log:          [PASS]
====================================================================
  >> ALL SYSTEMS OPERATIONAL: Ready for live hackathon evaluation. <<
```

### 2. Grounding & Anti-Hallucination Test Suite
Tests end-to-end OCR extraction from an uploaded valve scan, verifies that real telemetry (`68.5 N.m`, `7 drops/min`, `0.44mm`) appears in the generated `.docx`, ensures fake defaults are purged, and tests the negative critique guard on blank scans:
```powershell
.\.venv\Scripts\python.exe verify_grounding_suite.py
```

### 3. Hardened Sandbox Diagnostics
Verifies industrial hydraulic power calculation, 800×800 matrix memory allocation, and zero-egress network isolation:
```powershell
.\.venv\Scripts\python.exe verify_sandbox.py
```

### 4. Zero-Bypass RBAC Gatekeeper Test
Validates that file uploads strictly enforce lateral access boundaries and cannot circumvent the audit logger:
```powershell
.\.venv\Scripts\python.exe test_upload_rbac_and_audit.py
```

### 5. Cryptographic Audit Log Integrity Test
Validates the mathematical SHA-256 hash chain of `audit_log.jsonl`:
```powershell
.\.venv\Scripts\python.exe verify_audit.py
```

---

## 📡 API Reference

### Port 8000: Sovereign Agent Core & Multimodal Gateway
* `POST /api/v1/task`: Submits an industrial query or calculation task (enforces RBAC and model routing).
* `POST /api/v1/task/upload`: Uploads an engineering document or equipment photo (`.png`, `.jpg`, `.pdf`, `.txt`) for on-device OCR and grounded processing.
* `GET /health`: Returns gateway readiness and active system components.
* `GET /docs`: Interactive Swagger UI for live testing.

### Port 8001: Manoj Microservices & Knowledge Base
* `POST /kb/search`: Performs semantic RAG search across indexed documents, filtered by the caller's access role.
* `POST /generate/docx`: Generates branded Word approval notes and engineering compliance memos.
* `POST /generate/pptx`: Generates technical presentation decks.
* `POST /generate/xlsx`: Generates structured audit and telemetry spreadsheets.
* `POST /tools/run_code`: Executes sandboxed Python code with CPU and memory bounds.
* `GET /network/stats`: Returns real-time packet counters and egress status.

---

## 🎬 Live Demo Walkthrough for Evaluators

Here is the recommended 3-minute evaluation flow:

1. **Demonstrate Multimodal Grounding & Deliverable Generation**:
   - Run `verify_grounding_suite.py` or submit an inspection report image to `POST /api/v1/task/upload`.
   - Open the generated `.docx` in `manoj/outputs/`.
   - Show that the exact numbers extracted by on-device OCR appear in the document table with no hallucinated placeholders.
2. **Demonstrate Lateral RBAC Gatekeeping**:
   - Query an executive document (e.g., confidential vendor acquisition strategy) using the `Engineer` role: **Access Denied**.
   - Query the same document using the `VP` or `Executive` role: **Access Granted and Grounded**.
3. **Demonstrate Cryptographic Auditability**:
   - Open `audit_log.jsonl` and show the SHA-256 hashes linking each event to the previous one.
   - Run `verify_audit.py` to prove the audit chain is 100% untampered.
4. **Demonstrate Air-Gap Egress Protection**:
   - Query `GET http://127.0.0.1:8001/network/stats` to show zero bytes of outbound external data.

---

## 📁 Project Layout & Directory Structure

```text
SIH/
├── app/                             # Core Agent & Gateway (Punit)
│   ├── api/                         # REST routing and upload endpoints
│   ├── core/                        # LangGraph agent loop, RBAC policies, audit logger
│   ├── multimodal/                  # RapidOCR and local vision pipeline
│   ├── router/                      # Task classifier routing between models
│   ├── tools/                       # Tool registry & dynamic parameter bindings
│   └── main.py                      # FastAPI application entrypoint (Port 8000)
├── manoj/                           # Microservices & Tools (Manoj)
│   ├── data/                        # Sample SOPs and plant maintenance cards
│   ├── outputs/                     # Generated DOCX, PPTX, and XLSX deliverables
│   ├── code_sandbox.py              # Isolated Python execution sandbox
│   ├── doc_generator.py             # Enterprise document builder
│   ├── kb_search.py                 # Chroma vector RAG search
│   ├── network_monitor.py           # Network packet counter and egress checker
│   └── main.py                      # Microservices gateway entrypoint (Port 8001)
├── docker/                          # Sandbox containerization specs
│   ├── Dockerfile.sandbox           # Non-root, zero-network container definition
│   └── docker-compose.sandbox.yml   # Read-only filesystem and 1GB memory ceiling
├── models/                          # GGUF quantized model weights
├── scripts/                         # Startup and download scripts
│   ├── start_llama_server.ps1       # Windows GPU model launcher
│   └── start_llama_server.sh        # Linux GPU model launcher
├── audit_log.jsonl                  # Cryptographic tamper-evident audit ledger
├── verify_full_stack.py             # Master 4-pillar system verification
├── verify_sandbox.py                # Sandbox memory and isolation tests
├── verify_grounding_suite.py        # Multimodal OCR grounding and critique test
├── verify_audit.py                  # Audit hash chain mathematical verification
├── start_all.ps1                    # Master Windows orchestrator
├── start_all.sh                     # Master Linux orchestrator
└── README.md                        # Master documentation (this file)
```

---

## 👥 Team & Architecture Responsibilities
* **Punit**: Agent Core (LangGraph loop, neural routing, lateral RBAC gatekeeper, cryptographic audit ledger, grounding self-critique).
* **Manoj**: Retrieval & Microservices (Chroma RAG vector database, Office deliverable generators, code sandbox, network telemetry monitor).
* **Aparna**: Multimodal & Model Ops (Qwen2.5-VL vision integration, RapidOCR on-device pipeline, GPU serving configuration).
