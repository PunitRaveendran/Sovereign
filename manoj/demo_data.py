"""
demo_data.py — Seed the KB with synthetic demo documents.

Generates realistic industrial sample files that Rahul can use as demo assets:
  - 3 Inspection Reports (PDF-like text, different access levels)
  - 2 SOPs / Manuals
  - 1 Executive summary (executive-only)
  - 1 Handwritten-note simulation (plain text, to test OCR path)

Run:
    python demo_data.py          # generates .txt files in ./data/
    python demo_data.py --ingest # generates AND ingests into Chroma

These are the documents the agent will search during the live demo.
"""

from __future__ import annotations

import sys
from pathlib import Path

from config import settings
from rbac import AccessLevel

# ── Sample document definitions ───────────────────────────────────────────────

DOCUMENTS = [
    {
        "filename": "inspection_report_valve_assembly_01.txt",
        "access_level": AccessLevel.DEPARTMENT,
        "content": """\
INSPECTION REPORT — Valve Assembly Unit 7
Date: 2026-08-15
Inspector: A. Kumar
Location: Plant B, Bay 3

SUMMARY
-------
Full inspection of ball valve assembly (Unit 7) following routine maintenance
cycle. Valve body shows 3% wall-thickness reduction on the upstream flange,
within the 5% threshold defined in SOP-VAL-002. No active leak detected.

FINDINGS
--------
1. Upstream flange: wall thickness measured at 9.7mm (nominal: 10mm, min: 9.5mm).
   Status: ACCEPTABLE — monitor at next 3-month interval.
2. Actuator seal: light scoring on o-ring seating surface. Score depth < 0.1mm.
   Status: FLAG — replace o-ring at next planned shutdown.
3. Valve stem torque: 42 N·m (spec: 38–45 N·m). Status: PASS.
4. Visual: No visible corrosion on body. Coating intact.

RECOMMENDATION
--------------
Schedule o-ring replacement during Q4 planned shutdown (October 14–16, 2026).
Continue quarterly monitoring of flange thickness. No immediate action required.

REFERENCES
----------
- SOP-VAL-002: Ball Valve Inspection Procedure v3.1
- Engineering Drawing: ENG-0042-B, Rev 4
- Previous inspection: 2026-05-18 (all pass)

Inspector signature: _________________
""",
    },
    {
        "filename": "inspection_report_pump_seal_02.txt",
        "access_level": AccessLevel.DEPARTMENT,
        "content": """\
INSPECTION REPORT — Centrifugal Pump P-105 Seal Assembly
Date: 2026-08-22
Inspector: R. Sharma
Location: Plant A, Pump Room 2

SUMMARY
-------
Emergency inspection triggered by vibration alarm (Alert ID: ALR-20260822-047).
Mechanical seal found degraded beyond acceptable limits. Immediate shutdown
and seal replacement required.

FINDINGS
--------
1. Mechanical seal faces: 1.4mm wear groove detected. Limit per SOP-PMP-004 is 0.5mm.
   Status: FAIL — replace immediately.
2. Bearing housing temperature: 78°C (max allowable: 65°C).
   Status: FAIL — bearing replacement recommended.
3. Shaft runout: 0.08mm (max: 0.05mm). Status: FAIL.
4. Stuffing box: evidence of product leakage (fluid collected in drip pan).

RECOMMENDATION
--------------
Immediate shutdown of P-105. Replace mechanical seal with stock item SL-1048.
Inspect and replace bearing set. Perform shaft alignment check post-repair.
Estimated downtime: 18–24 hours.

REFERENCES
----------
- SOP-PMP-004: Centrifugal Pump Maintenance Procedure v2.0
- Vendor Bulletin: FlowTech TB-2026-11 (seal replacement guide)

Inspector signature: _________________
""",
    },
    {
        "filename": "inspection_report_electrical_panel_03.txt",
        "access_level": AccessLevel.MANAGEMENT,
        "content": """\
INSPECTION REPORT — MCC Panel 3 (Motor Control Centre)
Date: 2026-08-28
Inspector: P. Singh (Electrical)
Location: Plant C, Electrical Room

SUMMARY
-------
Annual thermographic inspection of MCC-3 as per Electrical Maintenance
Plan EMP-2026. Two overheating breakers detected. One requires replacement
before restart; one can wait until next planned maintenance window.

FINDINGS
--------
1. Breaker CB-22 (30A, feeder to compressor C-12):
   Surface temperature: 89°C. Baseline: 42°C. Delta: +47°C.
   Status: CRITICAL — replace before energising.
2. Breaker CB-31 (15A, lighting circuit):
   Surface temperature: 58°C. Baseline: 44°C. Delta: +14°C.
   Status: MONITOR — schedule replacement within 60 days.
3. Bus bar connections: all torque values within spec (47–52 N·m).
4. Arc flash PPE signage: current and compliant.

RECOMMENDATION
--------------
Replace CB-22 immediately. Replacement part: Square-D QO130, in stock.
Schedule CB-31 replacement by October 2026. Full re-thermograph after restart.

SAFETY NOTE: All work must follow LOTO procedure LOTO-ELEC-01.

Inspector signature: _________________
""",
    },
    {
        "filename": "sop_valve_inspection_SOP-VAL-002.txt",
        "access_level": AccessLevel.PUBLIC,
        "content": """\
STANDARD OPERATING PROCEDURE
SOP-VAL-002: Ball Valve Inspection Procedure
Version: 3.1 | Effective: 2025-01-01 | Review: 2027-01-01

1. SCOPE
   Applies to all ball valves DN15–DN200 in Plant A, B, and C.

2. FREQUENCY
   Routine: every 3 months.
   Triggered: after any process upset, abnormal vibration, or reported leak.

3. TOOLS REQUIRED
   - Ultrasonic thickness gauge (calibrated, cert within 12 months)
   - Torque wrench 10–100 N·m
   - Inspection mirror and torch
   - Drip-test kit (for leak-off measurement)

4. ACCEPTANCE CRITERIA
   4.1 Wall thickness: minimum 95% of nominal thickness as per drawing.
   4.2 Actuator torque: within ±10% of nameplate rating.
   4.3 Leakage: zero visible leakage at body-to-bonnet joint.
   4.4 Corrosion: no active pitting deeper than 0.3mm on pressure-retaining parts.

5. PROCEDURE
   Step 1: Isolate valve, depressurise, and lock-out per LOTO-MECH-01.
   Step 2: Clean external surfaces. Photograph current condition.
   Step 3: Measure wall thickness at 4 points on upstream and downstream flanges.
   Step 4: Record actuator torque (open and close cycles).
   Step 5: Perform visual inspection per Section 4.
   Step 6: Complete inspection form IF-VAL-002 and upload to CMMS.

6. FAILURE CRITERIA — IMMEDIATE ACTION REQUIRED
   - Wall thickness < 95% nominal → raise Work Order, do not return to service.
   - Visible leakage from body → immediate shutdown, notify supervisor.
   - Actuator torque outside ±20% → replace actuator.

7. REFERENCES
   Engineering Drawing Standard EDS-101, ASME B16.34, API 598.
""",
    },
    {
        "filename": "sop_pump_maintenance_SOP-PMP-004.txt",
        "access_level": AccessLevel.PUBLIC,
        "content": """\
STANDARD OPERATING PROCEDURE
SOP-PMP-004: Centrifugal Pump Maintenance Procedure
Version: 2.0 | Effective: 2024-06-01 | Review: 2026-06-01

1. SCOPE
   All centrifugal pumps in Plants A–C with power rating up to 75 kW.

2. MECHANICAL SEAL INSPECTION
   2.1 Maximum allowable seal face wear: 0.5mm groove depth.
   2.2 Replace seal if leakage exceeds 20 drops/minute from seal flush line.
   2.3 After replacement: run pump on water for 30 min before process restart.

3. BEARING INSPECTION
   3.1 Maximum housing temperature: 65°C (measured by contact thermometer).
   3.2 Vibration velocity: < 2.8 mm/s RMS per ISO 10816.
   3.3 Replace bearings at or above: temperature 75°C OR vibration 4.5 mm/s.

4. SHAFT ALIGNMENT
   4.1 Allowable parallel misalignment: 0.05mm.
   4.2 Allowable angular misalignment: 0.05mm/100mm.
   4.3 Use laser alignment tool; record values in form IF-PMP-004.

5. SEAL REPLACEMENT PROCEDURE
   Step 1: Isolate pump, drain casing, disconnect coupling.
   Step 2: Remove gland plate; extract old seal components.
   Step 3: Clean seal chamber and shaft sleeve. Inspect sleeve for scoring.
   Step 4: Install new seal per vendor assembly drawing.
   Step 5: Reassemble in reverse order; pressure-test at 1.5× operating pressure.
   Step 6: Complete Work Order and update equipment history card.

6. SPARE PARTS REFERENCE
   Standard mechanical seal: SL-1048 (FlowTech series 100).
   Bearing set: SKF 6209-2RS (standard), 6309-2RS (high-duty).
""",
    },
    {
        "filename": "executive_vendor_strategy_Q3.txt",
        "access_level": AccessLevel.EXECUTIVE,
        "content": """\
EXECUTIVE BRIEFING — Q3 2026 Vendor Negotiation Strategy
Classification: EXECUTIVE / BOARD ONLY
Prepared by: VP Operations
Date: 2026-07-30

STRATEGIC CONTEXT
-----------------
Our three primary MRO suppliers (ValveTech, FlowTech, ElectroParts) are due
for contract renewal in Q1 2027. Combined annual spend: USD 4.2M.
This briefing outlines negotiation leverage points and target price reductions.

TARGET OUTCOMES
---------------
1. ValveTech (valves, actuators): current rate USD 1.8M/yr.
   Target: 12% reduction to USD 1.58M via 3-year commitment.
   Leverage: two competing quotes from Asia-Pacific suppliers already obtained.
2. FlowTech (pump seals, bearings): current rate USD 1.4M/yr.
   Target: 8% reduction + 48-hour emergency delivery SLA.
   Leverage: recent quality issues (5 seal failures in 6 months, ref. reports above).
3. ElectroParts (electrical components): current rate USD 1.0M/yr.
   Target: hold on price, request consignment stock for top-10 fast-movers.

NEGOTIATION TIMELINE
--------------------
August 2026:  Issue formal RFQ to all three and two alternate suppliers.
October 2026: Review bids; shortlist to 2 per category.
November 2026: Final negotiation; target signed LOIs before year-end.

RISK
----
- FlowTech is sole-qualified for SL-1048 seal. Qualification of alternate
  supplier (Robco) requires 3-month test programme — initiate in Q4.
- ElectroParts consignment request may be declined; fallback: 90-day
  safety stock funded from capex budget line CAP-2026-07.

CONFIDENTIALITY: Do not share below VP level.
""",
    },
    {
        "filename": "handwritten_note_site_visit.txt",
        "access_level": AccessLevel.DEPARTMENT,
        "content": """\
[Simulated handwritten note — OCR output]

Site visit notes — B. Patel, 2026-08-20

Visited Plant B Bay 3 with A. Kumar.
Valve unit 7 — flange looks OK to me but Kumar flagged thickness reading.
Actuator feels stiff on close — torque was 42 Nm on the gauge.
O-ring seating has light score mark — photo taken.

Note to self: check if SOP-VAL-002 says to replace at 0.1mm score or
just flag it. Kumar says flag and monitor.

Mentioned to supervisor that next inspection should move to monthly
given the wear trend. Will follow up.

Also — pump room P-105 vibrating noticeably. Reported to maintenance.
""",
    },
]


def generate_files(output_dir: Path | None = None) -> list[Path]:
    """Write all demo documents to disk."""
    out = output_dir or settings.data_dir
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for doc in DOCUMENTS:
        p = out / doc["filename"]
        p.write_text(doc["content"], encoding="utf-8")
        print(f"  Created: {p.name} [access={doc['access_level'].value}]")
        paths.append(p)
    return paths


def ingest_all(output_dir: Path | None = None) -> None:
    """Generate and immediately ingest all demo documents."""
    from ingestor import ingest_file, get_collection
    collection = get_collection()
    out = output_dir or settings.data_dir
    paths = generate_files(out)

    doc_map = {d["filename"]: d["access_level"] for d in DOCUMENTS}
    total = 0
    for path in paths:
        level = doc_map.get(path.name, AccessLevel.PUBLIC)
        n = ingest_file(path, level, collection)
        total += n

    print(f"\n[OK] Ingested {len(paths)} documents -> {total} total chunks.")


if __name__ == "__main__":
    if "--ingest" in sys.argv:
        print("Generating + ingesting demo documents...")
        ingest_all()
    else:
        print("Generating demo documents (dry run — not ingested)...")
        paths = generate_files()
        print(f"\n✓ Created {len(paths)} files in {settings.data_dir}")
        print("Run with --ingest to load into Chroma.")
