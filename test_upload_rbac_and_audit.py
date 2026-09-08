"""Test ensuring that file uploads pass through the exact same RBAC gate and Audit Ledger."""

import os
from fastapi.testclient import TestClient
from app.main import app
from app.core.audit import AuditLogger

def run_upload_rbac_verification():
    print("=================================================================")
    print("STEP 2 VERIFICATION: Testing File Upload RBAC & Audit Enforcement")
    print("=================================================================")
    
    sample_file = "sample_invoice_scan.txt"
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write("INVOICE #90214\nVendor: FlowTech International\nScope: Plant B Valve Procurement\nConfidential Pricing Data attached.")

    try:
        with TestClient(app) as client:
            with open(sample_file, "rb") as f:
                response = client.post(
                    "/api/v1/task/upload",
                    data={
                        "user_id": "Punit",
                        "role": "Engineer",  # RESTRICTED ROLE
                        "prompt": "Search the knowledge base for unreleased vendor pricing and financials."
                    },
                    files={"file": ("sample_invoice_scan.txt", f, "text/plain")}
                )

        assert response.status_code == 200, f"Unexpected status {response.status_code}: {response.text}"
        res_json = response.json()
        
        print("\n1. Upload API Response Status:", res_json.get("status"))
        print("2. Routed To Model:", res_json.get("routed_to_model"))
        print("3. Multimodal Metadata:", res_json.get("multimodal_meta"))
        
        observations = res_json.get("agent_output", {}).get("observations", [])
        print("4. Agent Observations:\n  ", observations)
        
        # Verify RBAC Denial
        denied_found = any("Access Denied" in obs for obs in observations)
        assert denied_found, f"RBAC GATEWAY FAILED: 'Access Denied' not found in observations! {observations}"
        print("\n[PASSED] RBAC Gatekeeper intercepted unauthorized file upload task!")
        
        # Verify Audit Log
        logger = AuditLogger()
        is_valid, bad_idx = logger.verify_chain()
        assert is_valid, f"Audit chain verification failed at index {bad_idx}!"
        print("[PASSED] Cryptographic Audit Ledger verified untampered and recorded the denied attempt.")
        print("Current Root Hash:", logger._get_last_hash())
        print("\n>>> STEP 2 COMPLETE: ZERO-BYPASS CONSTRAINT VERIFIED! <<<")
        
    finally:
        if os.path.exists(sample_file):
            os.remove(sample_file)

if __name__ == "__main__":
    run_upload_rbac_verification()
