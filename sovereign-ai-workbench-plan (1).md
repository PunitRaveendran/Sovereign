# Sovereign — an air-gapped AI workbench for confidential industrial work

## One-line pitch
A self-hosted AI workbench that runs entirely on our own hardware, auto-picks the right open-weight model for each task, acts as a real agent (plans, uses tools, iterates), reads scanned/handwritten documents, produces real Word/PPT/Excel deliverables — and proves, at the hardware level, that nothing ever leaves the machine.

---

## 1. Architecture (built for 3× 8GB-class laptop GPUs, no inter-laptop networking)

**Hero laptop** (best single GPU, e.g. RTX 4060 or 5050, 8GB) runs the whole stack solo:
- FastAPI gateway
- Task router / model classifier
- Agent core (plan → act → observe → critique loop)
- Chroma vector DB (local knowledge base)
- All models, **hot-swapped in and out of VRAM** based on task type (not run concurrently — none of our GPUs can hold 2+ 7B models at once, so swapping is the right call, not a compromise)

**Air-gap laptop** (2nd machine): Wi-Fi + Bluetooth disabled at BIOS level, no Ethernet plugged in. Runs the identical stack fully offline. This is our strongest sovereignty proof — not a network log, a missing adapter.

**Portability laptop** (3rd machine): same config/model manifest, used live to show "add a model or node = edit a YAML file," answering the PS's "must support new models without redesign" requirement.

**Role-based access control (RBAC) layer**: enforced at the data layer, not the prompt layer. See section 3 below — this is a distinct architectural component, not a model instruction.

```
User request
   -> Task router (fast classifier, <150ms)
   -> loads correct model into VRAM (unloads previous)
   -> Agent core: plan -> call tool -> observe result -> self-critique -> repeat/finish
   -> Tools: code sandbox (no network), file read/write, KB search (Chroma), 
             office-file generator (docx/pptx/xlsx)
             [every tool call passes through the RBAC gate first]
   -> Output: real deliverable file + chat explanation
   -> Egress firewall (iptables/netns, network-less Docker) wraps entire pipeline
```

---

## 2. Models — a deliberately heterogeneous stack, not one family

We do **not** default to "one model family for everything." Each pick is chosen for a specific reason tied to our actual hardware or task, which is a stronger story for judges than "we used the popular open-weight model."

| Task | Model | Why this one, not Qwen-for-everything | Quant | Approx VRAM |
|---|---|---|---|---|
| Reasoning / document work / approval notes / agent core | **NVIDIA Nemotron 3 Nano 9B** (fallback: 4B variant) | Hybrid Mamba-Transformer, purpose-built by NVIDIA for RTX laptops via TensorRT-LLM; tuned hard for tool-calling and low hallucination — exactly what an agent core needs. Running the model NVIDIA optimized for our own silicon is a genuinely strong "why this model" answer in front of judges. | Q4_K_M / NVFP4 | ~5-6GB (9B) or ~3GB (4B) |
| Coding | **IBM Granite 4.1 8B** | Currently benchmarks ahead of same-size Qwen on HumanEval, built with tool-calling workflows in mind, Apache-licensed. A real non-Qwen alternative that holds up. | Q4_K_M | ~5GB |
| Vision / scanned docs / drawings | **Qwen2.5-VL-7B-Instruct** | Kept deliberately — still the strongest open vision-language model at a size that fits 8GB. NVIDIA's multimodal option (Nemotron Nano Omni) needs 16–25GB minimum even quantized, too big for our cards. Picking Qwen *only* where it's genuinely best-in-class, not everywhere, is the point. | Q4/AWQ | ~6GB |
| OCR fallback (pure text scans, handwriting) | PaddleOCR / Tesseract + easyOCR | CPU-friendly, no VRAM cost, good backstop when the vision model isn't needed | CPU | minimal |
| Embeddings for RAG | bge-small-en-v1.5 | fp16 | <1GB |
| Task router classifier (small, can stay resident in VRAM alongside a swapped model) | **Nemotron 3 Nano 4B** or **Gemma 3 4B** | Gemma 3 4B is the most memory-efficient option around (~4.2GB) — good if you want the router always loaded rather than swapped | tiny | ~3-4GB |
| CPU-only backup (insurance if a laptop's GPU/driver breaks mid-event) | Phi-4-mini (3.8B) | Runs with no GPU at all | CPU | minimal |

**Explicitly avoid:** OpenRouter, Ox Alpha, or any other hosted/API-only model. These are cloud services with no downloadable weights — using one would break the entire air-gap premise of the PS, no matter how good the benchmarks look.

Serving: **llama.cpp** (simplest, best swap speed, works well for Nemotron/Granite/Qwen GGUF builds) or **vLLM**/**TensorRT-LLM** if the team wants throughput and has time to set it up — TensorRT-LLM specifically is worth it for Nemotron since NVIDIA optimizes that path first. Recommend llama.cpp for the demo itself: model load/unload is fast and predictable, which matters live in front of judges.

---

## 3. Role-based access control (RBAC) — data-layer enforcement, not prompt-level

**Why this matters**: a flat knowledge base that everyone can query is worse than doing nothing manually — a leak becomes one well-phrased prompt away instead of requiring someone to physically access a locked room. Real orgs already segment access by role (web dev ≠ department lead ≠ VP/CEO); the assistant has to respect that, not flatten it.

**The core rule: never rely on the model to refuse.** Prompt-level instructions ("please don't share exec data with non-execs") are unreliable and can be talked around. Access has to be enforced *before* the data ever reaches the model — the model should physically never see what it isn't allowed to.

### How it works

1. **Tag at ingestion, not at query time.** Every document/chunk loaded into Chroma gets an `access_level` metadata tag when Manoj's ingestion pipeline processes it: `public`, `department`, `management`, `executive`. One-time cost at setup, not a runtime decision.
2. **Filter at retrieval — a hard metadata filter, not a suggestion.** Every KB query is scoped to the requesting user's allowed levels (`where: {access_level: {"$in": user_allowed_levels}}`). Restricted chunks are never in the candidate set the LLM sees — this is the actual security boundary.
3. **Gate every tool call the same way.** File read/write and document-search tools check the requesting user's role before touching a path or returning results. If the agent tries mid-task (on its own initiative) to read a restricted file, the tool call is rejected at the system layer and logged as a denial — not silently allowed and not left to the model's judgment.
4. **Local audit log.** Every access attempt — granted or denied — is logged locally. Doubles as a great live demo artifact and reinforces the "sovereign, auditable" pitch.

### Example role matrix (starting point — refine with Rahul)

| Role | Public docs | Department docs | Management docs | Executive/board docs |
|---|---|---|---|---|
| Web dev / general staff | ✅ | ❌ | ❌ | ❌ |
| Department lead | ✅ | ✅ | ❌ | ❌ |
| Management | ✅ | ✅ | ✅ | ❌ |
| VP / CEO | ✅ | ✅ | ✅ | ✅ |

### Who owns it
Extension of Manoj's knowledge-base/tools track: metadata tagging at ingestion, the Chroma retrieval filter, and the tool-call gate. **Rahul owns the role/permission matrix definition and the test cases that prove it holds** — a genuinely useful, well-scoped contribution: decide which roles exist, which document categories each should see, and write the query test set that confirms a web-dev-role login can never surface exec-tagged content.

### Demo addition
Log in as "web dev" role → ask something that touches restricted content (e.g. "summarize the Q3 vendor negotiation strategy") → denied/empty result, reason logged. Log in as "VP" role → same question → full grounded answer. Show the audit log listing both attempts side by side. ~30 seconds, makes the sovereignty story concrete instead of abstract, and directly answers "how do you stop internal misuse, not just external leaks."

---

## 4. Feature checklist mapped to the PS

- [x] Multi-model backend, auto-selected per task → router + hot-swap
- [x] New models addable without redesign → model manifest YAML, drop-in config
- [x] Agentic (plans, uses tools, iterates) → LangGraph plan-act-observe-critique loop
- [x] Local tools: file I/O, code sandbox, spreadsheet work, internal doc search
- [x] Multimodal: scanned PDFs, handwriting, drawings, photos, on-device OCR + vision
- [x] Real deliverables: docx/pptx/xlsx, working verified code, shown-steps calculations
- [x] Local knowledge base grounding (manuals, SOPs, correspondence) via Chroma RAG
- [x] Proof of zero external calls → hardware air-gap + egress firewall + live network monitor
- [x] Internal misuse / data-leak prevention → role-based access control enforced at retrieval and tool layers, not prompt-level (section 3)

### The innovation layer (what should push you into top 10)
0. **Deliberately heterogeneous model stack** — not one family for everything. NVIDIA Nemotron for the agent core (optimized for our exact RTX silicon via TensorRT-LLM), IBM Granite for coding, Qwen only for vision where it's still genuinely best-in-class. Each choice has a stated reason, which reads as engineering judgment rather than "we picked whatever's popular."
1. **Self-critique loop** — after drafting an approval note or running code, a second lightweight pass checks the output against the retrieved source documents before showing it as final. Catches hallucinated numbers instead of just producing them.
2. **VRAM-aware model swapping shown live** — turns a hardware constraint into a visible "efficient orchestration" feature, with a real-time VRAM graph on the dashboard.
3. **Hardware-level air gap** — a laptop with the Wi-Fi/Bluetooth radio physically disabled in BIOS, not just a software firewall. The strongest possible version of the sovereignty claim.
4. **Config-driven extensibility** — adding a model or a tool is a YAML edit, demoed live on the third laptop.

---

## 5. Team split (5 people)

**Punit — Agent core & orchestration (the spine of the project)**
- LangGraph plan → act → observe → critique loop
- Task router / classifier (train the tiny model or build the embedding-based classifier)
- Tool-calling interface (how the agent invokes sandbox, file I/O, KB search, doc-gen)
- Self-critique / grounding-check module
- Ties directly to your existing LangGraph + Chroma experience from ARIA — this is the highest-leverage seat, keep it.

**Aparna (3rd yr CS) — Multimodal pipeline + model ops**
- Integrate Qwen2-VL for scanned drawings/photos, PaddleOCR/Tesseract for text-heavy scans
- Handle model quantization and get all 3 models running cleanly on 6–8GB VRAM
- Build and test the model hot-swap logic (load/unload timing, VRAM monitoring)
- Sandbox security: Docker with `--network none` for the coding tool

**Manoj — Knowledge base, tools & document generation**
- Chroma ingestion pipeline: chunk and embed sample SOPs/manuals/reports
- Local knowledge-base search tool the agent calls
- Office-file generator tool: python-docx / python-pptx / openpyxl templates for approval notes, reports, sheets
- Egress firewall setup (iptables rules or Docker network isolation) + the live network monitor dashboard backend

**Abhinav — Frontend**
- Dashboard: chat interface, live router decision panel ("routing to Coder model..."), VRAM/model-swap visualizer, network-monitor visual (packets = 0), file preview/download for generated deliverables
- Keep it clean and legible — this is what judges actually look at for 80% of the demo, so polish here has outsized ROI

**Rahul (1st yr, no build experience yet) — Data, testing & demo assets**
This is a genuinely useful, well-scoped track — don't sideline him, give him ownership of it:
- Collect/create the demo dataset: 3–5 sample scanned inspection reports, a few sample SOPs/manuals for the knowledge base, one or two handwritten notes, a P&ID-style diagram image
- Write and label ~50–100 example task prompts ("summarize this," "write a function to...," "read this drawing") for training/testing the router classifier — a great low-risk way to contribute to the router's accuracy
- Run through every demo path repeatedly before the actual demo and log failures/edge cases (this job matters more than it sounds — most teams lose points to live-demo bugs no one caught)
- Help build the pitch deck / one-pager and rehearse the narration with whoever presents
- Pair with Aparna or Manoj for a few sessions to pick up basics — good on-ramp into the next project

---

## 6. Demo script (aim for ~6–8 min live)

1. **Router live-switch** (1 min): Ask a coding question, then a document question, back to back — show the dashboard picking a different model and the VRAM swap happening.
2. **End-to-end agentic task** (2–3 min): Feed a scanned inspection report → agent OCRs/reads it, pulls key findings grounded against the local SOP knowledge base, drafts and saves an actual Word approval note.
3. **Sandboxed coding task** (1–2 min): Ask for a small calculation/script, show it running and verified inside the network-less sandbox.
4. **Multimodal read** (1 min): Feed a handwritten note or drawing snippet, show correct extraction.
5. **Sovereignty proof** (1–2 min): Show the live network monitor at 0 packets throughout, then walk to the air-gap laptop and run one task with Wi-Fi physically off — the closing "mic drop" moment.

---

## 7. Build order (given hackathon time pressure)

1. Router + 2-model hot-swap working end-to-end (Punit + Aparna)
2. Sandboxed coding demo (Aparna + Manoj)
3. KB ingestion + doc-gen tool (Manoj)
4. Agent loop wiring it all together + critique pass (Punit)
5. OCR/vision pipeline (Aparna)
6. Frontend dashboard (Abhinav, can start in parallel from hour 1 against mocked data)
7. Air-gap laptop mirror + egress firewall (Manoj, late but before final rehearsal)
8. Dataset, router training examples, rehearsal (Rahul, ongoing from hour 1)

Build in this order so that even if you run out of time, you always have *something* fully working to show rather than five half-built features.
