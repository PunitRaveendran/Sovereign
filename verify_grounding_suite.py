import os
import sys
from pathlib import Path
import requests
from docx import Document
from PIL import Image, ImageDraw

def run_suite():
    # TEST 1: POSITIVE GROUNDED CASE
    print("=================================================================")
    print("TEST 1: POSITIVE GROUNDED CASE (REAL TELEMETRY FROM SCANNED SCAN)")
    print("=================================================================")
    img = Image.new('RGB', (800, 320), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    content = """ASSET INSPECTION LOG: BALL VALVE BV-999
Date: 2026-09-04
Technician ID: TECH-409
Inspection Results:
- Wall Thickness: 91.2% (FAIL - minimum allowable: 95.0%)
- Actuator Torque: 68.5 N.m (FAIL - exceeds 55.0 N.m limit)
- Bonnet Flange Leakage: 7 drops/min observed
- Maximum Pitting Depth: 0.44mm (FAIL - permissible: 0.30mm)
Disposition: Quarantine asset immediately and flag for maintenance overhaul."""
    d.text((25, 25), content, fill=(0, 0, 0))
    img.save("grounded_case.png")

    url = "http://127.0.0.1:8000/api/v1/task/upload"
    with open("grounded_case.png", "rb") as f:
        res = requests.post(
            url,
            files={"file": ("grounded_case.png", f, "image/png")},
            data={"user_id": "auditor_1", "role": "Engineer", "prompt": "Review the attached report and generate an approval note docx."},
            timeout=60
        )
    assert res.status_code == 200, f"Upload failed: {res.text}"
    data1 = res.json()
    obs1 = data1.get("agent_output", {}).get("observations", [])
    critique1 = data1.get("agent_output", {}).get("final_output", "")
    print(f"Observations: {obs1}")
    print(f"Critique Output:\n{critique1.encode('ascii', errors='replace').decode('ascii')}")

    # Inspect the newest docx
    output_dir = Path(r"c:\Users\Punit Raveendran\Desktop\SIH\manoj\outputs")
    docx_files = sorted(output_dir.glob("*.docx"), key=os.path.getmtime, reverse=True)
    doc1 = Document(str(docx_files[0]))
    text1 = "\n".join([p.text for p in doc1.paragraphs if p.text.strip()])

    print("\n--- Grounding Assertions on DOCX ---")
    for expected in ["68.5 N.m", "0.44mm", "7"]:
        assert expected in text1, f"Missing expected metric: {expected}"
        print(f"  [PASS] Extracted metric '{expected}' grounded in Word document!")
    for fake in ["96.5%", "48 N.m", "0.12mm"]:
        assert fake not in text1, f"Hardcoded default was found: {fake}"
        print(f"  [PASS] Hardcoded fake default '{fake}' is absent from document.")
    print("  [PASS] Positive grounded flow verified!")

    # TEST 2: NEGATIVE CASE (BLANK IMAGE - UNGROUNDED TELEMETRY)
    print("\n=================================================================")
    print("TEST 2: NEGATIVE CASE (BLANK IMAGE / UNGROUNDED)")
    print("=================================================================")
    blank = Image.new('RGB', (400, 200), color=(255, 255, 255))
    blank.save("blank_case.png")

    with open("blank_case.png", "rb") as f:
        res2 = requests.post(
            url,
            files={"file": ("blank_case.png", f, "image/png")},
            data={"user_id": "auditor_1", "role": "Engineer", "prompt": "Review the attached report and generate an approval note docx."},
            timeout=60
        )
    assert res2.status_code == 200, f"Upload failed: {res2.text}"
    data2 = res2.json()
    obs2 = data2.get("agent_output", {}).get("observations", [])
    critique2 = data2.get("agent_output", {}).get("final_output", "")
    print(f"Observations: {obs2}")
    print(f"Critique Output:\n{critique2.encode('ascii', errors='replace').decode('ascii')}")

    assert any(k in critique2 for k in ["LOW CONFIDENCE", "IN_PROGRESS", "manual inspection", "Awaiting"]), f"Critique failed to flag ungrounded status: {critique2}"
    print("  [PASS] Critique successfully intercepted ungrounded input (refused fabrication, flagged low confidence or in-progress)!")

    print("\n=================================================================")
    print("ALL VERIFICATIONS PASSED: 100% GROUNDING INTEGRITY CONFIRMED")
    print("=================================================================")

if __name__ == "__main__":
    run_suite()
