# Sovereign — Manoj's Components

> **Air-gapped AI Workbench** | Knowledge Base, Tools & Document Generation

---

## What lives here

| File | What it does |
|---|---|
| `config.py` | Central settings — all paths + params in one place, `.env` overrideable |
| `rbac.py` | Role-based access control: access-level enums, role permissions matrix, audit logger, RBAC gate |
| `ingestor.py` | CLI + library to chunk, embed, tag, and store documents into Chroma |
| `kb_search.py` | KB search tool for the agent — RBAC enforced at retrieval (FastAPI `/kb/*`) |
| `doc_generator.py` | DOCX / PPTX / XLSX generator from structured content dicts (FastAPI `/generate/*`) |
| `network_monitor.py` | Live network packet counter + iptables/Docker egress setup (FastAPI `/network/*`) |
| `main.py` | Unified gateway — mounts all three services on a single port |
| `demo_data.py` | Seeds Chroma with realistic industrial demo documents at 4 access levels |
| `tests/` | RBAC + doc generator test suite (Rahul's test cases here) |

---

## Quick start

```bash
cd sovereign/manoj

# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and edit .env (GPU users: set EMBEDDING_DEVICE=cuda)
cp .env.example .env

# 3. Generate + ingest demo documents
python demo_data.py --ingest

# 4. Start the unified API
uvicorn main:app --host 127.0.0.1 --port 8001 --reload

# 5. Verify: http://127.0.0.1:8001/docs  (Swagger UI)
```

---

## Ingestor CLI

```bash
# Ingest a single file with an access level tag
python ingestor.py ingest ./data/sop_valve_inspection.txt --access-level public

# Ingest an entire directory (recursive)
python ingestor.py ingest ./data --access-level department

# Ingest an executive-only document
python ingestor.py ingest ./data/exec_strategy.pdf --access-level executive

# List what's in the KB
python ingestor.py list

# Clear the KB (careful!)
python ingestor.py clear --yes
```

Supported file types: **PDF, DOCX, TXT, MD, PNG, JPG, TIFF** (OCR on images via Tesseract).

---

## KB Search (agent tool interface)

```python
from kb_search import search_kb
from rbac import Role

# The agent calls this — RBAC filter applied automatically
result = search_kb(
    query="What is the acceptance criterion for valve wall thickness?",
    user="alice",
    role=Role.WEB_DEV,   # Only sees public chunks
)

# Inject into LLM prompt
context = result.as_context_string()
```

REST call:
```bash
curl -X POST http://127.0.0.1:8001/kb/search \
  -H "Content-Type: application/json" \
  -d '{"query": "pump seal failure criteria", "user": "alice", "role": "department_lead"}'
```

---

## Document Generator

```python
from doc_generator import generate_docx, generate_pptx, generate_xlsx

# Approval note
path = generate_docx("approval_note", {
    "title": "Valve Assembly Inspection — Unit 7",
    "summary": "Inspection passed. O-ring replacement scheduled for Q4 shutdown.",
    "findings": ["Wall thickness 9.7mm — within 95% nominal", "O-ring: light score, flag only"],
    "recommendation": "Return to service. Schedule o-ring at Q4 shutdown.",
    "access_level": "department",
})

# Findings presentation
path = generate_pptx("findings_deck", {
    "title": "Plant B Inspection Findings — August 2026",
    "findings": [
        {"heading": "Valve Unit 7", "body": "Wall thickness OK, o-ring flagged."},
        {"heading": "Pump P-105",   "body": "Mechanical seal failed — immediate replacement."},
    ],
})

# Data table
path = generate_xlsx("data_table", {
    "title": "Equipment Status August 2026",
    "headers": ["Asset", "Status", "Inspector", "Next Action"],
    "rows": [
        ["Valve 7",   "PASS",   "A. Kumar",  "O-ring Q4"],
        ["Pump P-105","FAIL",   "R. Sharma", "Immediate seal replace"],
        ["MCC-3 CB22","CRITICAL","P. Singh", "Replace before restart"],
    ],
})
```

REST call:
```bash
curl -X POST http://127.0.0.1:8001/generate/docx \
  -H "Content-Type: application/json" \
  -d '{"template": "approval_note", "content": {"title": "Test", "summary": "Test summary"}}'
```

---

## Network Monitor

```bash
# Start the monitor (included in main.py, runs automatically)
# Or run standalone:
python network_monitor.py

# Poll current stats
curl http://127.0.0.1:8001/network/stats

# List interfaces
curl http://127.0.0.1:8001/network/interfaces

# SSE stream (dashboard subscribes here)
curl -N http://127.0.0.1:8001/network/stream

# Get egress setup scripts
curl http://127.0.0.1:8001/network/egress-rules
```

Generate the iptables + Docker firewall scripts:
```bash
python network_monitor.py egress
# Writes: ./egress/setup_egress.sh
#         ./egress/docker-compose.egress.yml
```

---

## RBAC — access levels and role matrix

| Role | public | department | management | executive |
|---|:---:|:---:|:---:|:---:|
| `web_dev` | ✓ | | | |
| `department_lead` | ✓ | ✓ | | |
| `management` | ✓ | ✓ | ✓ | |
| `vp_ceo` | ✓ | ✓ | ✓ | ✓ |

Access is enforced at the **Chroma retrieval level**, not at the prompt level.
The model physically never sees restricted chunks.

**Audit log** is at `audit.log` (configurable). Read via:
```bash
curl http://127.0.0.1:8001/kb/audit?n=20
```

---

## Running tests

```bash
# Install pytest
pip install pytest

# Run RBAC tests (Rahul owns these)
pytest tests/test_rbac.py -v

# Run doc generator tests
pytest tests/test_doc_generator.py -v

# Run everything
pytest tests/ -v
```

---

## Live demo flow (Manoj + Abhinav)

1. **Ingest** `python demo_data.py --ingest` (one-time before demo)
2. **Start API** `uvicorn main:app --port 8001`
3. **RBAC demo**: Agent logs in as `web_dev`, asks about Q3 vendor strategy → empty result, audit log shows denial. Logs in as `vp_ceo` → full answer.
4. **Doc gen demo**: Agent generates an approval note DOCX from an inspection report → dashboard shows download link.
5. **Network proof**: Dashboard network monitor shows `packets_sent_per_sec = 0` throughout.

---

## Interface for Punit (agent core)

The agent calls these tools over loopback HTTP:

| Tool | Endpoint | Method |
|---|---|---|
| Search KB | `POST /kb/search` | `{query, user, role, k}` |
| Read audit log | `GET /kb/audit` | — |
| Generate DOCX | `POST /generate/docx` | `{template, content, filename}` |
| Generate PPTX | `POST /generate/pptx` | `{template, content, filename}` |
| Generate XLSX | `POST /generate/xlsx` | `{template, content, filename}` |
| Download file | `GET /generate/download/{filename}` | — |
| Network stats | `GET /network/stats` | — |
| Network stream | `GET /network/stream` | SSE |

All endpoints documented at `http://127.0.0.1:8001/docs`.
