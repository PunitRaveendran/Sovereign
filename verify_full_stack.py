"""
verify_full_stack.py — End-to-End System Diagnostics for Sovereign AI Workbench
Tests and verifies all 4 system pillars:
  [1] Port 8080: Local LLM Engine (llama-server)
  [2] Port 8001: Manoj's Microservices (Chroma KB, DocGen, Network, Sandbox)
  [3] Port 8000: Punit's Agent Core & RBAC Gatekeeper
  [4] Data Integrity: Cryptographic Tamper-Evident Audit Chain
"""

import sys
import json
import time
import requests
from pathlib import Path

def print_header(title):
    print("\n" + "=" * 68)
    print(f"  {title}")
    print("=" * 68)

def test_llm_engine():
    print_header("PILLAR 1: LOCAL LLM INFERENCE ENGINE (Port 8080)")
    url = "http://127.0.0.1:8080/v1/chat/completions"
    payload = {
        "model": "local-model",
        "messages": [{"role": "user", "content": "Respond with the single word: ONLINE"}],
        "max_tokens": 20
    }
    try:
        r = requests.post(url, json=payload, timeout=25)
        if r.status_code == 200:
            data = r.json()
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            print("  [STATUS]  ONLINE")
            print(f"  [SERVER]  HTTP 200 OK")
            print(f"  [REPLY]   {reply[:80]}")
            return True
        else:
            print(f"  [STATUS]  HTTP {r.status_code}: {r.text[:100]}")
            return False
    except Exception as e:
        print(f"  [STATUS]  OFFLINE ({type(e).__name__})")
        print("  [HINT]    Ensure llama-server is running on port 8080 (run .\\scripts\\start_llama_server.ps1).")
        return False

def test_manoj_microservices():
    print_header("PILLAR 2: TOOL & RETRIEVAL MICROSERVICES (Port 8001)")
    base_url = "http://127.0.0.1:8001"
    all_ok = True

    # 1. Main Health
    try:
        r = requests.get(f"{base_url}/health", timeout=3)
        if r.status_code == 200:
            h = r.json()
            print("  [CORE]    ONLINE (Manoj Gateway)")
            print(f"  [SANDBOX] Backend: {h.get('sandbox_backend', 'unknown').upper()}")
        else:
            print(f"  [CORE]    HTTP {r.status_code}")
            all_ok = False
    except Exception as e:
        print(f"  [CORE]    OFFLINE ({type(e).__name__})")
        return False

    # 2. Chroma KB
    try:
        r_kb = requests.get(f"{base_url}/kb/health", timeout=3)
        if r_kb.status_code == 200:
            doc_cnt = r_kb.json().get("doc_count", 0)
            print(f"  [CHROMA]  ONLINE (Indexed documents: {doc_cnt})")
        else:
            print(f"  [CHROMA]  HTTP {r_kb.status_code}")
            all_ok = False
    except Exception:
        print("  [CHROMA]  UNAVAILABLE")
        all_ok = False

    # 3. Network Monitor
    try:
        r_net = requests.get(f"{base_url}/network/health", timeout=3)
        if r_net.status_code == 200:
            print("  [NETWORK] Telemetry Monitor: ACTIVE")
    except Exception:
        print("  [NETWORK] Telemetry Monitor: UNAVAILABLE")

    return all_ok

def test_agent_core():
    print_header("PILLAR 3: AGENT CORE & LATERAL RBAC GATE (Port 8000)")
    task_url = "http://127.0.0.1:8000/api/v1/task"
    payload = {
        "user_id": "System_Diagnostic",
        "role": "Engineer",
        "task_description": "Calculate refinery pump head loss with math."
    }
    try:
        r = requests.post(task_url, json=payload, timeout=35)
        if r.status_code == 200:
            data = r.json()
            agent_out = data.get("agent_output", {})
            obs = agent_out.get("observations", ["No observations"])
            print("  [STATUS]  ONLINE")
            print(f"  [ROUTER]  Model Route: {data.get('routed_to_model', 'Default')}")
            print(f"  [EXEC]    Obs: {obs[0][:80]}...")
            return True
        else:
            print(f"  [STATUS]  HTTP {r.status_code}: {r.text[:100]}")
            return False
    except Exception as e:
        print(f"  [STATUS]  OFFLINE ({type(e).__name__})")
        print("  [HINT]    Ensure python -m app.main is running on port 8000.")
        return False

def test_cryptographic_audit():
    print_header("PILLAR 4: CRYPTOGRAPHIC TAMPER-EVIDENT AUDIT CHAIN")
    try:
        from app.core.audit import AuditLogger
        logger = AuditLogger()
        root_hash = logger._get_last_hash()
        is_valid, bad_idx = logger.verify_chain()

        print(f"  [ROOT HASH] {root_hash}")
        if is_valid:
            print("  [CHAIN]     VALID & MATHEMATICALLY UNTAMPERED (100% Verified)")
            return True
        else:
            print(f"  [CHAIN]     TAMPER DETECTED AT ENTRY INDEX #{bad_idx}")
            return False
    except Exception as e:
        print(f"  [AUDIT]     Check failed: {e}")
        return False

def main():
    print("\n" + "#" * 68)
    print("      SOVEREIGN AI WORKBENCH — FULL SYSTEM HEALTH VERIFICATION")
    print("#" * 68)

    t1 = test_llm_engine()
    t2 = test_manoj_microservices()
    t3 = test_agent_core()
    t4 = test_cryptographic_audit()

    print("\n" + "=" * 68)
    print("                      DIAGNOSTIC SUMMARY")
    print("=" * 68)
    print(f"  1. LLM Serving Engine (:8080):       {'[PASS]' if t1 else '[FAIL]'}")
    print(f"  2. Manoj's Microservices (:8001):     {'[PASS]' if t2 else '[FAIL]'}")
    print(f"  3. Punit's Agent Core (:8000):        {'[PASS]' if t3 else '[FAIL]'}")
    print(f"  4. Cryptographic Audit Log:          {'[PASS]' if t4 else '[FAIL]'}")
    print("=" * 68)

    if t1 and t2 and t3 and t4:
        print("\n  >> ALL SYSTEMS OPERATIONAL: Ready for live hackathon evaluation. <<\n")
        sys.exit(0)
    else:
        print("\n  >> ONE OR MORE SERVICES NOT READY. Check logs above. <<\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
