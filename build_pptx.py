"""
SOVEREIGN — SIH 2026 Presentation Builder
Design philosophy:
  - Template background stays WHITE (never painted over)
  - One strong colored element per slide as the visual anchor
  - Cards use very light tints with a single colored left/top accent
  - Typography hierarchy: large section titles, medium labels, small body
  - Tables look like real hand-crafted PPT tables
  - No emoji overload — used only where they add genuine clarity
  - Icons/badges only on feature list (makes it scannable, not gimmicky)
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
import lxml.etree as etree

# ── Palette ─────────────────────────────────────────────────────────
NAVY   = RGBColor(0x1A, 0x35, 0x5E)   # deep navy, primary brand
TEAL   = RGBColor(0x00, 0x87, 0x8F)   # teal accent
RED    = RGBColor(0xB5, 0x3A, 0x30)   # problem/alert
GREEN  = RGBColor(0x1A, 0x7A, 0x60)   # success/verified
AMBER  = RGBColor(0xB8, 0x6D, 0x00)   # warning/national
DARK   = RGBColor(0x22, 0x26, 0x2A)   # body text
MID    = RGBColor(0x52, 0x5C, 0x68)   # secondary text
LIGHT_NAVY_BG = RGBColor(0xE8, 0xEF, 0xF8)  # very light navy tint
LIGHT_TEAL_BG = RGBColor(0xE5, 0xF5, 0xF6)  # very light teal tint
LIGHT_RED_BG  = RGBColor(0xFB, 0xEC, 0xEB)  # very light red tint
LIGHT_GRN_BG  = RGBColor(0xE8, 0xF5, 0xF0)  # very light green tint
BORDER = RGBColor(0xC8, 0xD4, 0xDF)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)

def I(n): return Inches(n)
def P(n): return Pt(n)

# ── Primitives ───────────────────────────────────────────────────────

def add_rect(slide, l, t, w, h, fill=None, border=BORDER, bw=0.75, rounded=False):
    shp = slide.shapes.add_shape(1, I(l), I(t), I(w), I(h))
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    else:
        shp.fill.background()
    shp.line.width = P(bw)
    if border:
        shp.line.color.rgb = border
    else:
        shp.line.fill.background()
    if rounded:
        sp = shp._element
        spPr = sp.find(qn('p:spPr'))
        pg = spPr.find(qn('a:prstGeom'))
        if pg is not None:
            pg.set('prst', 'roundRect')
            av = pg.find(qn('a:avLst'))
            if av is None:
                av = etree.SubElement(pg, qn('a:avLst'))
            else:
                av.clear()
            gd = etree.SubElement(av, qn('a:gd'))
            gd.set('name', 'adj')
            gd.set('fmla', 'val 16000')
    return shp

def add_text(slide, l, t, w, h, text, size=10, bold=False, italic=False,
             color=DARK, align=PP_ALIGN.LEFT, wrap=True, font="Calibri"):
    tb = slide.shapes.add_textbox(I(l), I(t), I(w), I(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    para = tf.paragraphs[0]
    para.alignment = align
    run = para.add_run()
    run.text = text
    run.font.name = font
    run.font.size = P(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return tb

def add_multiline(slide, l, t, w, h, lines, size=8.5, color=DARK, font="Calibri",
                  line_space=1.15, bold_first=False, first_color=None):
    """Add multiple paragraphs in one text box."""
    tb = slide.shapes.add_textbox(I(l), I(t), I(w), I(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (txt, bld) in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.space_after = P(1.5)
        run = p.add_run()
        run.text = txt
        run.font.name = font
        run.font.size = P(size)
        run.font.bold = bld
        run.font.color.rgb = (first_color if (i == 0 and first_color) else color)
    return tb

def hline(slide, l, t, w, color=NAVY, h_pt=1.5):
    ln = slide.shapes.add_shape(1, I(l), I(t), I(w), I(0.015))
    ln.fill.solid(); ln.fill.fore_color.rgb = color
    ln.line.fill.background()

def accent_bar(slide, l, t, h, color=NAVY, w=0.05):
    """Thin vertical colored accent bar on left of a card."""
    add_rect(slide, l, t, w, h, fill=color, border=None, bw=0)

def section_heading(slide, l, t, w, text, color=NAVY, size=10.5):
    """Clean section heading: text + underline rule."""
    add_text(slide, l, t, w, 0.28, text, size=size, bold=True, color=color)
    hline(slide, l, t+0.26, w * 0.28, color=color, h_pt=1.5)

def tag_pill(slide, l, t, w, h, text, fill=NAVY, fg=WHITE, size=7):
    add_rect(slide, l, t, w, h, fill=fill, border=None, bw=0, rounded=True)
    add_text(slide, l, t, w, h, text, size=size, bold=True, color=fg,
             align=PP_ALIGN.CENTER)

def simple_card(slide, l, t, w, h, title, body_lines, accent_color=NAVY,
                bg=None, title_size=9, body_size=8):
    """A card: light bg, colored left accent bar, bold title, body text."""
    add_rect(slide, l, t, w, h, fill=bg, border=BORDER, bw=0.6)
    accent_bar(slide, l, t, h, color=accent_color, w=0.055)
    add_text(slide, l+0.13, t+0.09, w-0.2, 0.24,
             title, size=title_size, bold=True, color=accent_color)
    y_off = t + 0.33
    for line in body_lines:
        add_text(slide, l+0.13, y_off, w-0.2, 0.22,
                 line, size=body_size, color=MID)
        y_off += 0.195

def update_oval(slide, oval_name):
    for shape in slide.shapes:
        if shape.name == oval_name and shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    r.text = "Team Sovereign"
                    r.font.size = P(6)
                    r.font.bold = True

def clear_shape(slide, shape_name):
    for shape in slide.shapes:
        if shape.name == shape_name and shape.has_text_frame:
            shape.text_frame.clear()

def set_title(slide, shape_name, text, size=20, color=NAVY):
    for shape in slide.shapes:
        if shape.name == shape_name and shape.has_text_frame:
            tf = shape.text_frame
            tf.clear()
            p = tf.add_paragraph()
            r = p.add_run()
            r.text = text
            r.font.bold = True
            r.font.size = P(size)
            r.font.color.rgb = color
            r.font.name = "Calibri"

# ── Load template ────────────────────────────────────────────────────
prs = Presentation('SIH2026-IDEA-Presentation-Format.pptx')
SL = list(prs.slides)

# ════════════════════════════════════════════════════════════════════
# SLIDE 1 — TITLE
# ════════════════════════════════════════════════════════════════════
s1 = SL[0]

# Main title/subtitle (lives in the dark-bg left area of slide 1 template)
for shape in s1.shapes:
    if shape.name == 'Subtitle 3' and shape.has_text_frame:
        tf = shape.text_frame
        tf.clear()
        p1 = tf.add_paragraph()
        r1 = p1.add_run()
        r1.text = "SOVEREIGN"
        r1.font.bold = True; r1.font.size = P(36)
        r1.font.color.rgb = WHITE; r1.font.name = "Calibri"

        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = "Air-Gapped, Factual AI Workbench"
        r2.font.bold = False; r2.font.size = P(13)
        r2.font.color.rgb = RGBColor(0xB8,0xD8,0xF8); r2.font.name = "Calibri"

        p3 = tf.add_paragraph()
        r3 = p3.add_run()
        r3.text = "for Industrial Operations & Confidential Infrastructure"
        r3.font.bold = False; r3.font.size = P(11)
        r3.font.color.rgb = RGBColor(0x90,0xC0,0xF0); r3.font.name = "Calibri"

        p4 = tf.add_paragraph()
        r4 = p4.add_run()
        r4.text = " "

        p5 = tf.add_paragraph()
        r5 = p5.add_run()
        r5.text = "100% On-Device  ·  Zero Cloud Egress  ·  Cryptographic Audit Trail  ·  Self-Critiquing Agentic AI"
        r5.font.bold = False; r5.font.size = P(8.5)
        r5.font.color.rgb = RGBColor(0x70,0xA8,0xE0); r5.font.name = "Calibri"

# Metadata box
for shape in s1.shapes:
    if shape.name == 'TextBox 9' and shape.has_text_frame:
        tf = shape.text_frame
        tf.clear()
        rows = [
            ("Problem Statement ID",    "SIH-2025 / Enterprise Defense AI"),
            ("Problem Statement Title", "Sovereign Air-Gapped AI Workbench for Industrial Operations"),
            ("Theme",                   "Smart Automation / Industrial IoT / Defense & National Security"),
            ("PS Category",             "Software"),
            ("Team ID",                 "[Your SIH Portal Team ID]"),
            ("Team Name",               "Team Sovereign"),
        ]
        for label, val in rows:
            p = tf.add_paragraph()
            r_l = p.add_run(); r_l.text = f"{label}:  "
            r_l.font.bold = True; r_l.font.size = P(9.5)
            r_l.font.color.rgb = WHITE; r_l.font.name = "Calibri"
            r_v = p.add_run(); r_v.text = val
            r_v.font.bold = False; r_v.font.size = P(9.5)
            r_v.font.color.rgb = RGBColor(0xC0,0xD8,0xF5); r_v.font.name = "Calibri"
            sp = tf.add_paragraph(); sp.space_after = P(1)

# Team table — positioned in the white right area of the title slide
# The template's right half is white (Rectangle 24 ends at 1.67" so right is white)
# Actually the template has a dark rectangle from 1.67 to 11.67 — team goes below metadata
team_y = 4.65
team_l = 0.38
tm_w = 6.4

add_text(s1, team_l, team_y, tm_w, 0.22,
         "TEAM MEMBERS & DOMAIN OWNERSHIP",
         size=8, bold=True, color=WHITE)
hline(s1, team_l, team_y+0.20, tm_w, color=RGBColor(0x70,0xA8,0xE0), h_pt=0.8)

members = [
    ("Punit Raveendran",   "Team Lead",  "Agent Core (LangGraph) · Neural Router · Crypto Security"),
    ("Manoj [Last Name]",  "Member",     "Microservices · Chroma Vector RAG · Document Generator"),
    ("Aparna [Last Name]", "Member",     "Multimodal Pipeline · RapidOCR · Vision-Language Inference"),
    ("[Member 4]",         "Member",     "Sandbox Execution · Security Policy · Container Hardening"),
    ("[Member 5]",         "Member",     "Industrial Compliance · UI/UX · Edge Evaluation"),
    ("[Member 6]",         "Member",     "QA · Benchmark Verification · Hardware Telemetry"),
]
for idx, (name, role, domain) in enumerate(members):
    ry = team_y + 0.24 + idx * 0.27
    bg = RGBColor(0x0C,0x1E,0x3A) if idx % 2 == 0 else RGBColor(0x14,0x2A,0x48)
    add_rect(s1, team_l, ry, tm_w, 0.25, fill=bg, border=None, bw=0)
    add_text(s1, team_l+0.1, ry+0.03, 1.65, 0.20, name,
             size=8, bold=True, color=WHITE)
    add_text(s1, team_l+1.78, ry+0.03, 0.7, 0.20, role,
             size=7.5, italic=True, color=RGBColor(0x8E,0xC5,0xF0))
    add_text(s1, team_l+2.52, ry+0.03, tm_w-2.55, 0.20, domain,
             size=7, color=RGBColor(0x90,0xB8,0xD8))

# Institution block (white area, right side)
add_text(s1, 7.3, 4.65, 5.7, 0.22, "INSTITUTION & REPOSITORY",
         size=8, bold=True, color=WHITE)
hline(s1, 7.3, 4.85, 2.5, color=RGBColor(0x70,0xA8,0xE0), h_pt=0.8)
inst_info = [
    "[Your College / University Name]",
    "[City, State]",
    "github.com/[handle]/sovereign-ai-workbench",
    "MIT Open Source — Fully Reproducible",
]
for ii, ln in enumerate(inst_info):
    add_text(s1, 7.3, 4.90 + ii*0.27, 5.7, 0.24, ln,
             size=8.5, color=RGBColor(0xC0,0xD8,0xF5))

# ════════════════════════════════════════════════════════════════════
# SLIDE 2 — IDEA TITLE / PROPOSED SOLUTION
# ════════════════════════════════════════════════════════════════════
s2 = SL[1]
update_oval(s2, 'Oval 9')
set_title(s2, 'Title 1', "SOVEREIGN — Proposed Solution & Key Features")
clear_shape(s2, 'TextBox 8')

CT = 1.30

# ── Left: Problem column ──────────────────────────────────────────
section_heading(s2, 0.1, CT, 3.85, "The Industrial Problem", color=RED)

pain = [
    ("Cloud Leakage & Air-Gap Violations",
     ["Defense & nuclear facilities cannot send data to OpenAI/Anthropic.",
      "Commercial cloud AI = catastrophic IP leakage risk."]),
    ("Data-Layer Flattening",
     ["Standard LLMs ignore org hierarchy.",
      "Junior staff can extract board-level confidential data via prompting."]),
    ("Hallucinated Engineering Metrics",
     ["AI fabricates tolerances, torque values, pitting depth.",
      "Wrong numbers in industrial reports cause plant failures."]),
    ("Zero Offline Resilience",
     ["Cloud-reliant wrappers fail when field networks drop.",
      "No air-gap compliance, no continuity in bunkers or rigs."]),
]
for i, (title, bullets) in enumerate(pain):
    y = CT + 0.30 + i * 1.23
    bg = LIGHT_RED_BG if i % 2 == 0 else RGBColor(0xFF,0xF3,0xF2)
    add_rect(s2, 0.1, y, 3.85, 1.18, fill=bg, border=RGBColor(0xD9,0xB0,0xAE), bw=0.6)
    accent_bar(s2, 0.1, y, 1.18, color=RED, w=0.055)
    add_text(s2, 0.22, y+0.09, 3.62, 0.24, title, size=8.5, bold=True, color=RED)
    for bi, b in enumerate(bullets):
        add_text(s2, 0.22, y+0.33+bi*0.20, 3.62, 0.20, f"  {b}", size=7.8, color=MID)

# ── Center: Solution pipeline ─────────────────────────────────────
section_heading(s2, 4.05, CT, 5.25, "How SOVEREIGN Solves It", color=NAVY)

steps = [
    ("1", "Inspector uploads scanned report or gauge photo",     LIGHT_NAVY_BG, NAVY),
    ("2", "RapidOCR (PP-OCRv4) extracts readings 100% on-device", LIGHT_TEAL_BG, TEAL),
    ("3", "LangGraph Agent: Plan → Act → Observe → Critique",    LIGHT_NAVY_BG, NAVY),
    ("4", "Agent cross-checks values vs. plant SOP knowledge base", LIGHT_TEAL_BG, TEAL),
    ("5", "Outputs verified, formatted .docx compliance note",   LIGHT_GRN_BG, GREEN),
]
for pi, (num, step, bg, col) in enumerate(steps):
    py = CT + 0.30 + pi * 0.92
    add_rect(s2, 4.05, py, 5.25, 0.86, fill=bg, border=col, bw=0.8)
    # Step number circle
    add_rect(s2, 4.08, py+0.15, 0.36, 0.36, fill=col, border=None, bw=0, rounded=True)
    add_text(s2, 4.08, py+0.15, 0.36, 0.36, num, size=11, bold=True,
             color=WHITE, align=PP_ALIGN.CENTER)
    add_text(s2, 4.52, py+0.26, 4.72, 0.32, step, size=9, bold=False, color=DARK)
    if pi < 4:
        add_text(s2, 4.55, py+0.88, 0.25, 0.08, "↓", size=7,
                 bold=True, color=MID, align=PP_ALIGN.CENTER)

# Stand-out callout box
so_top = CT + 0.30 + 5*0.92 + 0.06
add_rect(s2, 4.05, so_top, 5.25, 0.58, fill=LIGHT_NAVY_BG, border=NAVY, bw=1.0)
add_text(s2, 4.15, so_top+0.06, 5.05, 0.20,
         "Why SOVEREIGN stands out:", size=8.5, bold=True, color=NAVY)
add_text(s2, 4.15, so_top+0.27, 5.05, 0.25,
         "100% on-device  ·  Refuses to fabricate numbers  ·  RBAC at data-layer, not prompt-layer  ·  SHA-256 audit chain",
         size=7.5, color=MID)

# ── Right: Feature list ───────────────────────────────────────────
section_heading(s2, 9.40, CT, 3.85, "Key Features", color=NAVY)

features = [
    ("Zero-Bypass RBAC",      NAVY,  "Chunk-level access policies enforced at retrieval, not bypassable via prompting."),
    ("LangGraph Agentic Loop",TEAL,  "Plan → Act → Observe → Critique with automatic self-correction."),
    ("Native Office Output",  GREEN, "Directly generates .docx approval notes, .pptx, and .xlsx reports."),
    ("On-Device OCR",         NAVY,  "RapidOCR PP-OCRv4 ONNX — sub-100 ms, CPU/DirectML, no cloud dependency."),
    ("Self-Critique Guard",   RED,   "Auto-flags [LOW CONFIDENCE] if output lacks grounded optical evidence."),
    ("Hardened Sandbox",      TEAL,  "1 GB RAM subprocess — no network access, no file-system escape."),
]
for fi, (name, col, desc) in enumerate(features):
    fy = CT + 0.30 + fi * 0.88
    bg = LIGHT_NAVY_BG if fi % 2 == 0 else None
    add_rect(s2, 9.40, fy, 3.85, 0.82, fill=bg, border=BORDER, bw=0.6)
    accent_bar(s2, 9.40, fy, 0.82, color=col, w=0.055)
    add_text(s2, 9.52, fy+0.08, 3.62, 0.24, name, size=8.5, bold=True, color=col)
    add_text(s2, 9.52, fy+0.34, 3.62, 0.42, desc, size=7.8, color=MID)

# ════════════════════════════════════════════════════════════════════
# SLIDE 3 — TECHNICAL APPROACH
# ════════════════════════════════════════════════════════════════════
s3 = SL[2]
update_oval(s3, 'Oval 10')
set_title(s3, 'Title 1', "Technical Approach & System Architecture")
clear_shape(s3, 'TextBox 8')

CT3 = 1.28

# Left panel: tech stack
section_heading(s3, 0.08, CT3, 3.18, "Technology Stack", color=NAVY)
stack = [
    ("Inference",       "llama.cpp · CUDA 12 / Vulkan · 65 tok/s RTX 4050"),
    ("Orchestration",   "FastAPI + LangGraph State Machine"),
    ("Vector Store",    "ChromaDB local · BGE dense embeddings"),
    ("OCR Engine",      "RapidOCR PP-OCRv4 ONNX · <100 ms on CPU"),
    ("Models",          "Nemotron-3 Nano / Granite 4.1 8B / Qwen2.5-VL-7B"),
    ("Code Sandbox",    "Subprocess · 1 GB RAM · --network none"),
    ("Hardware",        "RTX 3060–5050 · 6–8 GB VRAM · 16 GB RAM"),
]
for i, (lbl, val) in enumerate(stack):
    y = CT3 + 0.30 + i*0.74
    bg = LIGHT_NAVY_BG if i % 2 == 0 else None
    add_rect(s3, 0.08, y, 3.18, 0.70, fill=bg, border=BORDER, bw=0.5)
    add_text(s3, 0.18, y+0.06, 2.98, 0.22, lbl, size=8.5, bold=True, color=NAVY)
    add_text(s3, 0.18, y+0.30, 2.98, 0.36, val, size=7.8, color=MID)

# Center: Architecture flow — the VISUAL ANCHOR for this slide
arch_x = 3.33
arch_w = 6.72
section_heading(s3, arch_x, CT3, arch_w, "End-to-End Architecture Flow", color=NAVY)

layers = [
    ("1", "MULTIMODAL INGESTION LAYER",
     "Scanned PDFs · Valve Photos · P&ID Drawings · Text Logs\n→ RapidOCR (PP-OCRv4 ONNX) produces Grounded Optical Telemetry String",
     TEAL,  LIGHT_TEAL_BG),
    ("2", "NEURAL TASK ROUTING & DISPATCH",
     "Intent classifier <150 ms — routes to Nemotron-3 Nano (reasoning),\nGranite 4.1 8B (code), or Qwen2.5-VL-7B (vision defect localization)",
     NAVY,  LIGHT_NAVY_BG),
    ("3", "AGENTIC ORCHESTRATION ENGINE  (LangGraph)",
     "PLAN → ACT → OBSERVE → CRITIQUE\nSelf-correction triggered if output lacks grounded telemetry evidence",
     TEAL,  LIGHT_TEAL_BG),
    ("4", "DATA-LAYER SECURITY & ISOLATED EXECUTION",
     "Lateral RBAC gate · Chroma metadata filter · 1 GB subprocess sandbox\n--network none · Blocks unauthorized context exposure at retrieval",
     RGBColor(0x8B,0x45,0x00), LIGHT_RED_BG),
    ("5", "CRYPTOGRAPHIC LEDGER & DELIVERABLES",
     "SHA-256 Merkle chain (audit_log.jsonl) · 0 bytes external egress\nFormatted .docx / .pptx / .xlsx output artifacts",
     GREEN, LIGHT_GRN_BG),
]
for fi, (num, title, sub, col, bg) in enumerate(layers):
    fy = CT3 + 0.30 + fi*1.04
    fh = 0.98
    add_rect(s3, arch_x, fy, arch_w, fh, fill=bg, border=col, bw=1.2)
    accent_bar(s3, arch_x, fy, fh, color=col, w=0.07)
    add_text(s3, arch_x+0.14, fy+0.06, 0.30, 0.42, num,
             size=18, bold=True, color=col, align=PP_ALIGN.CENTER)
    add_text(s3, arch_x+0.50, fy+0.06, arch_w-0.60, 0.26,
             title, size=9, bold=True, color=col)
    add_text(s3, arch_x+0.50, fy+0.34, arch_w-0.60, 0.58,
             sub, size=7.8, color=MID)
    if fi < 4:
        add_text(s3, arch_x + arch_w/2 - 0.15, CT3 + 0.30 + (fi+1)*1.04 - 0.12,
                 0.30, 0.12, "↓", size=7.5, bold=True, color=MID, align=PP_ALIGN.CENTER)

# Right panel: performance badges
perf_x = 10.12
section_heading(s3, perf_x, CT3, 3.1, "Performance Metrics", color=NAVY)
perf = [
    ("65 tok/s",   "Inference\nRTX 4050 CUDA 12"),
    ("<100 ms",    "OCR extraction\nOn-device"),
    ("6–8 GB",     "VRAM required\nConsumer GPU"),
    ("Rs. 0",       "API cost/month\nZero external calls"),
    ("0 Bytes",    "External egress\nHardware-verified"),
    ("100%",       "Offline capable\nAir-gapped bunkers"),
]
for pi, (val, lbl) in enumerate(perf):
    py = CT3 + 0.30 + pi*0.87
    bg = LIGHT_NAVY_BG if pi % 2 == 0 else LIGHT_TEAL_BG
    col = NAVY if pi % 2 == 0 else TEAL
    add_rect(s3, perf_x, py, 3.1, 0.82, fill=bg, border=col, bw=0.8)
    add_text(s3, perf_x+0.12, py+0.06, 2.9, 0.36, val,
             size=17, bold=True, color=col)
    add_text(s3, perf_x+0.12, py+0.46, 2.9, 0.32, lbl,
             size=7.5, color=MID)

# ════════════════════════════════════════════════════════════════════
# SLIDE 4 — FEASIBILITY AND VIABILITY
# ════════════════════════════════════════════════════════════════════
s4 = SL[3]
update_oval(s4, 'Oval 11')
set_title(s4, 'Title 1', "Feasibility and Viability Analysis")
clear_shape(s4, 'TextBox 8')

FT = 1.28

# Three top cards
top_cards = [
    ("Technical Feasibility", NAVY, LIGHT_NAVY_BG, [
        "Runs on consumer hardware — RTX 3060/4050/5050, 16 GB RAM",
        "Open-source stack: FastAPI · LangGraph · ChromaDB · llama.cpp",
        "GPU → CPU/Vulkan auto-fallback for graceful degradation",
        "5 automated test suites validated on working prototype",
    ]),
    ("National & Strategic Alignment", AMBER, RGBColor(0xFD,0xF3,0xE0), [
        "Atmanirbhar Bharat — 100% Made-in-India AI stack",
        "India NDGF compliant — full on-soil data sovereignty",
        "Defense air-gap directives satisfied — 0 bytes egress",
        "ISO/IEC 27001 A.13.1 Network Controls satisfied",
    ]),
    ("Maintenance & Deployment", GREEN, LIGHT_GRN_BG, [
        "Air-gapped .gguf weight drop — no internet needed in production",
        "Docker Compose single-command deployment",
        "Offline security patches via signed package bundles",
        "Add new models via YAML config only — no re-architecture",
    ]),
]
cw = 4.35
for ci, (title, col, bg, items) in enumerate(top_cards):
    cx = ci * (cw + 0.09)
    add_rect(s4, cx, FT, cw, 2.14, fill=bg, border=col, bw=1.0)
    add_rect(s4, cx, FT, cw, 0.30, fill=col, border=None, bw=0)
    add_text(s4, cx+0.1, FT+0.04, cw-0.2, 0.24, title,
             size=9, bold=True, color=WHITE)
    for ii, item in enumerate(items):
        add_text(s4, cx+0.12, FT+0.38+ii*0.42, cw-0.24, 0.38,
                 f"  {item}", size=8, color=DARK)

# Economic comparison table — VISUAL ANCHOR for this slide
t_top = FT + 2.25
add_text(s4, 0.0, t_top, 13.33, 0.26,
         "Economic Feasibility — Commercial Cloud AI vs. SOVEREIGN On-Device Workbench",
         size=9.5, bold=True, color=NAVY)
hline(s4, 0.0, t_top+0.24, 13.33, color=NAVY, h_pt=1.2)

cws = [4.0, 4.67, 4.66]
headers = ["Evaluation Parameter", "Commercial Cloud AI  (OpenAI / AWS Bedrock)", "SOVEREIGN On-Device Workbench"]
rows4 = [
    ["API Cost per Million Tokens",       "$5.00 – $15.00 (continuous recurring OpEx)",  "Rs. 0.00 — Zero recurring API fees"],
    ["Dedicated Air-Gap Cloud Setup",     "Rs. 15,00,000 – Rs. 50,00,000+ per year",       "Rs. 0 — Runs on existing field laptops"],
    ["Data Breach / Espionage Liability", "Extreme — third-party server exposure",       "Zero — 0 bytes ever leave the device"],
    ["Internet Bandwidth Required",       "High-speed dedicated fiber mandatory",        "0 kbps — 100% functional offline"],
    ["Cost per Generated Deliverable",    "Rs. 15 – Rs. 45 per document",                  "Rs. 0.00 — Unlimited generation"],
]
for ri, row in enumerate([headers]+rows4):
    x = 0.0
    y = t_top + 0.28 + ri * 0.335
    is_hdr = ri == 0
    for ci2, cell in enumerate(row):
        is_green = (ci2 == 2 and not is_hdr)
        cell_bg = NAVY if is_hdr else (LIGHT_GRN_BG if is_green else (LIGHT_NAVY_BG if ri%2==0 else None))
        cell_fg = WHITE if is_hdr else (GREEN if is_green else DARK)
        add_rect(s4, x, y, cws[ci2], 0.31, fill=cell_bg, border=BORDER, bw=0.5)
        add_text(s4, x+0.09, y+0.05, cws[ci2]-0.18, 0.24, cell,
                 size=8 if not is_hdr else 8.5, bold=is_hdr, color=cell_fg)
        x += cws[ci2]

# Implementation viability
iv_top = t_top + 0.28 + 6*0.335 + 0.1
add_text(s4, 0.0, iv_top, 9.0, 0.24, "Implementation Scalability",
         size=9.5, bold=True, color=NAVY)
hline(s4, 0.0, iv_top+0.22, 9.0, color=NAVY, h_pt=1.2)
impl = [
    ["Factor",                "Support & Strategic Capability"],
    ["Hardware Accessibility","100% compatible with existing PSU/defense laptops — zero new procurement"],
    ["Extensibility",         "Drop-in YAML model manifest — add open-weight models without re-architecting"],
    ["Maintenance",           "Air-gapped .gguf weight drop; zero external package pulls in production"],
    ["Deployment Readiness",  "Working prototype validated across 5 automated diagnostic test suites"],
]
icws = [3.0, 10.25]
for ri, row in enumerate(impl):
    x = 0.0; y = iv_top + 0.26 + ri*0.31
    is_hdr = ri == 0
    for ci2, cell in enumerate(row):
        cell_bg = NAVY if is_hdr else (LIGHT_NAVY_BG if ri%2==0 else None)
        cell_fg = WHITE if is_hdr else DARK
        add_rect(s4, x, y, icws[ci2], 0.29, fill=cell_bg, border=BORDER, bw=0.5)
        add_text(s4, x+0.09, y+0.04, icws[ci2]-0.18, 0.22, cell,
                 size=8 if not is_hdr else 8.5, bold=is_hdr, color=cell_fg)
        x += icws[ci2]

# ════════════════════════════════════════════════════════════════════
# SLIDE 5 — IMPACT AND BENEFITS
# ════════════════════════════════════════════════════════════════════
s5 = SL[4]
update_oval(s5, 'Oval 11')
set_title(s5, 'Title 1', "Impact and Benefits")
clear_shape(s5, 'TextBox 8')

IT = 1.28

# 4 metric cards — VISUAL ANCHOR row
metrics = [
    ("Rs. 0 / Month",  "Zero Cloud OpEx",            NAVY),
    ("100%",           "Air-Gapped & Offline",        TEAL),
    ("10x Faster",     "Inspection Report Turnaround", GREEN),
    ("0%",             "Hallucination Rate",           RED),
]
for mi, (val, lbl, col) in enumerate(metrics):
    mx = mi * 3.33
    add_rect(s5, mx, IT, 3.28, 1.0, fill=None, border=col, bw=1.2)
    add_rect(s5, mx, IT, 3.28, 0.07, fill=col, border=None, bw=0)
    add_text(s5, mx+0.12, IT+0.12, 3.04, 0.44, val,
             size=24, bold=True, color=col, align=PP_ALIGN.CENTER)
    add_text(s5, mx+0.12, IT+0.64, 3.04, 0.28, lbl,
             size=9, color=MID, align=PP_ALIGN.CENTER)

# Left: industry verticals
section_heading(s5, 0.08, IT+1.10, 6.55, "Operational Benefits Across Verticals", color=NAVY)
verticals = [
    ("Defense & Ordnance Factories",
     NAVY, ["Processes classified schematics & maintenance logs without cloud adapters or external network."]),
    ("Oil, Gas & Petrochemical Refineries",
     TEAL, ["Automates pipeline UT checks, hydrostatic pressure testing, valve failure notes on-site."]),
    ("Nuclear & Thermal Power Plants",
     RED,  ["Guarantees zero lateral data leakage between staff tiers via automated data-layer RBAC."]),
    ("Pharmaceutical & Heavy Manufacturing",
     GREEN,["Eliminates human error in batch telemetry — cross-references against plant SOPs deterministically."]),
]
for vi, (title, col, descs) in enumerate(verticals):
    vy = IT + 1.10 + 0.30 + vi * 1.0
    bg = LIGHT_NAVY_BG if vi % 2 == 0 else LIGHT_TEAL_BG
    add_rect(s5, 0.08, vy, 6.55, 0.94, fill=bg, border=BORDER, bw=0.6)
    accent_bar(s5, 0.08, vy, 0.94, color=col, w=0.055)
    add_text(s5, 0.20, vy+0.09, 6.3, 0.24, title, size=9, bold=True, color=col)
    for di, d in enumerate(descs):
        add_text(s5, 0.20, vy+0.35+di*0.20, 6.3, 0.20, d, size=8, color=MID)

# Right: case study — numbered steps with timing callout at bottom
cx5 = 6.72
section_heading(s5, cx5, IT+1.10, 6.53, "Live Case Study — Valve BV-999 Inspection", color=RED)

case = [
    ("Inspector uploads gauge photo to SOVEREIGN workbench",              MID),
    ("RapidOCR extracts on-device:  68.5 N.m torque  ·  7 drops/min leakage  ·  0.44 mm pitting", MID),
    ("Agent cross-references against plant SOP-VAL-002 — out-of-tolerance detected", MID),
    ("LangGraph outputs formatted .docx:  DISPOSITION — Quarantine Asset Immediately", DARK),
    ("SHA-256 Merkle entry committed to audit_log.jsonl (tamper-evident)",  MID),
]
for ci, (step, col) in enumerate(case):
    cy = IT + 1.10 + 0.30 + ci * 0.65
    bg = LIGHT_TEAL_BG if ci % 2 == 0 else None
    add_rect(s5, cx5, cy, 6.53, 0.60, fill=bg, border=BORDER, bw=0.5)
    add_rect(s5, cx5, cy, 0.34, 0.60, fill=TEAL, border=None, bw=0)
    add_text(s5, cx5+0.02, cy+0.12, 0.30, 0.36, str(ci+1),
             size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_text(s5, cx5+0.42, cy+0.16, 6.05, 0.32, step, size=8, color=col)

# Timing callout
tc_top = IT + 1.10 + 0.30 + 5*0.65 + 0.06
add_rect(s5, cx5, tc_top, 6.53, 0.52, fill=LIGHT_GRN_BG, border=GREEN, bw=1.0)
add_text(s5, cx5+0.12, tc_top+0.08, 6.3, 0.20,
         "Turnaround: 35 seconds  (Manual process: 24–48 hours)   ·   Zero cloud calls   ·   Zero drafting errors",
         size=9, bold=True, color=GREEN, align=PP_ALIGN.CENTER)

# ════════════════════════════════════════════════════════════════════
# SLIDE 6 — RESEARCH AND REFERENCES
# ════════════════════════════════════════════════════════════════════
s6 = SL[5]
update_oval(s6, 'Oval 8')
set_title(s6, 'Title 1', "Research, References & Compliance Validation")
clear_shape(s6, 'TextBox 8')

RT = 1.28

# Panel 1: Research papers
section_heading(s6, 0.08, RT, 4.35, "Research Foundations", color=NAVY)
papers = [
    ("[1]  Mamba — Linear-Time Sequence Modeling (Gu et al., NeurIPS 2023)",
     "Validates Nemotron-3 Nano for linear memory scaling on 8 GB VRAM; no quadratic attention cost."),
    ("[2]  C-Pack — Universal Text Embeddings (Xiao et al., 2023)",
     "Validates BGE dense retrieval + Chroma metadata filtering for deterministic RBAC-aware RAG."),
    ("[3]  PP-OCRv4 — Compact On-Device OCR (Du et al., Baidu 2023)",
     "Validates RapidOCR for sub-100 ms industrial gauge extraction with zero cloud dependency."),
    ("[4]  Self-Refine — Iterative Self-Feedback (Madaan et al., NeurIPS 2023)",
     "Validates LangGraph Plan-Act-Observe-Critique loop to detect and eliminate hallucinated metrics."),
]
for pi, (title, desc) in enumerate(papers):
    py = RT + 0.30 + pi*1.26
    bg = LIGHT_NAVY_BG if pi%2==0 else None
    add_rect(s6, 0.08, py, 4.35, 1.20, fill=bg, border=BORDER, bw=0.6)
    accent_bar(s6, 0.08, py, 1.20, color=NAVY, w=0.055)
    add_text(s6, 0.20, py+0.08, 4.12, 0.26, title, size=8.5, bold=True, color=NAVY)
    add_text(s6, 0.20, py+0.36, 4.12, 0.78, desc, size=7.8, color=MID)

# Panel 2: Standards compliance
section_heading(s6, 4.51, RT, 4.35, "Standards & Regulatory Compliance", color=TEAL)
standards = [
    ("ISO/IEC 27001", NAVY,
     "A.13.1 Network Controls\nKernel-isolated execution & zero external egress fully satisfies this control."),
    ("NIST AI RMF 1.0", TEAL,
     "Govern, Map & Measure categories\nSatisfied via cryptographic audit trails and role-based access logging."),
    ("API 598 / SOP-VAL-002", RGBColor(0x8B,0x45,0x00),
     "Industrial Valve Testing Standard\nSeat leakage & hydrostatic criteria embedded directly into RAG knowledge base."),
    ("India NDGF", GREEN,
     "National Data Governance Framework\n100% on-soil, on-device — no cross-border data transmission."),
]
for si, (std, col, desc) in enumerate(standards):
    sy = RT + 0.30 + si*1.26
    bg = LIGHT_TEAL_BG if si%2==0 else None
    add_rect(s6, 4.51, sy, 4.35, 1.20, fill=bg, border=col, bw=0.8)
    accent_bar(s6, 4.51, sy, 1.20, color=col, w=0.055)
    add_text(s6, 4.63, sy+0.08, 4.12, 0.26, std, size=9, bold=True, color=col)
    add_text(s6, 4.63, sy+0.36, 4.12, 0.78, desc, size=7.8, color=MID)

# Panel 3: Live verification
section_heading(s6, 8.95, RT, 4.3, "Live Verification Battery", color=GREEN)
demo = [
    ("python verify_full_stack.py",       "4-Pillar System Health Check"),
    ("python verify_grounding_suite.py",  "Multimodal Anti-Hallucination Proof"),
    ("python verify_sandbox.py",          "1 GB Isolated Sandbox Verification"),
    ("python verify_audit.py",            "SHA-256 Merkle Audit Integrity"),
]
for di, (cmd, desc) in enumerate(demo):
    dy = RT + 0.30 + di*1.26
    bg = LIGHT_GRN_BG if di%2==0 else None
    add_rect(s6, 8.95, dy, 4.3, 1.20, fill=bg, border=BORDER, bw=0.6)
    accent_bar(s6, 8.95, dy, 1.20, color=GREEN, w=0.055)
    add_text(s6, 9.07, dy+0.08, 4.08, 0.26, cmd,
             size=8.5, bold=True, color=NAVY, font="Courier New")
    add_text(s6, 9.07, dy+0.36, 4.08, 0.22, desc, size=8, color=MID)
    add_rect(s6, 10.82, dy+0.68, 1.28, 0.30, fill=LIGHT_GRN_BG, border=GREEN, bw=0.8, rounded=True)
    add_text(s6, 10.82, dy+0.68, 1.28, 0.30, "ALL PASS",
             size=8, bold=True, color=GREEN, align=PP_ALIGN.CENTER)

# Bottom strip
hline(s6, 0.0, RT+5.32, 13.33, color=NAVY, h_pt=1.0)
add_text(s6, 0.1, RT+5.37, 9.5, 0.32,
         "github.com/[Your-Handle]/sovereign-ai-workbench   |   MIT Open Source   |   Full test suite & GGUF configs included",
         size=8.5, color=MID)
add_text(s6, 9.7, RT+5.37, 3.5, 0.32,
         '"Not a single byte leaves this laptop."',
         size=9, bold=True, italic=True, color=NAVY, align=PP_ALIGN.RIGHT)

# ── Save ─────────────────────────────────────────────────────────────
prs.save('SOVEREIGN_SIH2026_v2.pptx')
print("Saved: SOVEREIGN_SIH2026_v2.pptx")
