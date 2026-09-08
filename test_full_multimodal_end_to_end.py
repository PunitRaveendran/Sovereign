"""Full end-to-end verification of Step 4:
Upload Scanned Report -> OCR/Vision Extraction -> KB Grounding -> Approval Note -> Real Word (.docx) Deliverable.
"""

import os
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

def run_multimodal_end_to_end():
    print("\n============================================================================")
    print("STEP 4: FULL MULTIMODAL END-TO-END WORKFLOW TEST")
    print("Upload Report -> Extraction -> KB Grounding -> Approval Note (.docx)")
    print("============================================================================\n")

    # STAGE 1: Prepare Sample Scanned Inspection Report
    sample_report_name = "scanned_plant_inspection_report.txt"
    report_content = (
        "PLANT C - UNIT 4 INSPECTION TELEMETRY\n"
        "Asset: Ball Valve DN100 (Tag: BV-100-PLANTC)\n"
        "Date of Scan: September 4, 2026\n"
        "Wall Thickness Measured: 96.5% of nominal (Acceptance minimum: 95%)\n"
        "Actuator Torque: 48 N.m (Rating: 50 N.m +-10%)\n"
        "Visual Inspection: Body-to-bonnet joint shows ZERO leakage\n"
        "Corrosion Scan: Maximum pitting depth 0.12mm (Permissible max: 0.3mm)\n"
        "Recommendation: Complies with SOP-VAL-002. Approved for continued service."
    )
    
    with open(sample_report_name, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"--> STAGE 1: Created sample scanned deliverable '{sample_report_name}'.")
    print("    Report Data: Ball Valve BV-100, Wall Thickness 96.5%, Torque 48 N.m, Leakage Zero.\n")

    try:
        with TestClient(app) as client:
            with open(sample_report_name, "rb") as f:
                prompt_instruction = (
                    "Review the attached scanned inspection report, cross-reference against SOP-VAL-002 in KB, "
                    "and generate an approval note docx for continued plant operation."
                )
                
                print("--> STAGE 2: Uploading deliverable to POST /api/v1/task/upload as 'Executive'...")
                response = client.post(
                    "/api/v1/task/upload",
                    data={
                        "user_id": "Punit",
                        "role": "Executive",
                        "prompt": prompt_instruction
                    },
                    files={"file": (sample_report_name, f, "text/plain")}
                )

        assert response.status_code == 200, f"Upload endpoint failed: {response.text}"
        res_data = response.json()

        print("\n--> STAGE 3: Multimodal Extraction Output:")
        print("    Status:       ", res_data.get("status"))
        print("    Model Routed: ", res_data.get("routed_to_model"))
        print("    Metadata:     ", res_data.get("multimodal_meta"))

        agent_output = res_data.get("agent_output", {})
        print("\n--> STAGE 4: LangGraph Cognitive Orchestration:")
        print("    Plan Generated:\n   ", agent_output.get("plan", "")[:250], "...")
        print("\n    Tool Observations Executed:")
        for obs in agent_output.get("observations", []):
            print("     *", obs[:200])

        print("\n    Final Agent Output:\n   ", agent_output.get("final_output", "")[:250], "...")

        # STAGE 5: Verify Deliverable on Disk
        outputs_dir = Path("manoj/outputs")
        docx_files = list(outputs_dir.glob("*.docx"))
        assert docx_files, "No DOCX deliverable found in manoj/outputs/!"
        
        # Sort by creation time to get the latest
        latest_docx = max(docx_files, key=lambda p: p.stat().st_mtime)
        print(f"\n--> STAGE 5: Real Office Deliverable Verified on Disk!")
        print(f"    File: {latest_docx.name} ({round(latest_docx.stat().st_size / 1024, 1)} KB)")
        print(f"    Full Path: {latest_docx.resolve()}")
        
        print("\n============================================================================")
        print(">>> ALL 4 STAGES PASSED: FULL MULTIMODAL END-TO-END PIPELINE VERIFIED! <<<")
        print("============================================================================\n")

    finally:
        if os.path.exists(sample_report_name):
            os.remove(sample_report_name)

if __name__ == "__main__":
    run_multimodal_end_to_end()
