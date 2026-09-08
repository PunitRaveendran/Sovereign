import httpx, json

base = "http://127.0.0.1:8001"

# Use a long timeout — embedding model takes ~35s on first load
client = httpx.Client(timeout=120)

# 1. Health check
r = client.get(f"{base}/health")
print("[1] Health:", r.json()["status"])

# 2. KB search as web_dev (should only see public docs)
r = client.post(f"{base}/kb/search", json={
    "query": "valve wall thickness criteria",
    "user": "alice", "role": "web_dev"
})
res = r.json()
print(f"[2] KB search web_dev: {len(res['chunks'])} chunks")
for c in res["chunks"][:2]:
    print(f"    -> {c['filename']} (access={c['access_level']})")

# 3. KB search as vp_ceo (should see everything, incl. executive)
r = client.post(f"{base}/kb/search", json={
    "query": "vendor negotiation strategy Q3",
    "user": "punit_vp", "role": "vp_ceo"
})
res = r.json()
print(f"[3] KB search vp_ceo: {len(res['chunks'])} chunks")
for c in res["chunks"][:2]:
    print(f"    -> {c['filename']} (access={c['access_level']})")

# 4. Generate a DOCX approval note
r = client.post(f"{base}/generate/docx", json={
    "template": "approval_note",
    "content": {
        "title": "Valve 7 Inspection Approval",
        "summary": "Inspection passed. O-ring flagged for Q4 replacement.",
        "findings": ["Wall thickness 9.7mm - within 95% nominal", "Actuator torque 42 Nm - PASS"],
    },
    "filename": "demo_approval"
})
res = r.json()
print(f"[4] DOCX generated: {res['filename']}")

# 5. Audit log
r = client.get(f"{base}/kb/audit?n=5")
recs = r.json()["records"]
print(f"[5] Audit log: {len(recs)} records")
for rec in recs:
    print(f"    user={rec['user']} granted={rec['granted']} level={rec['requested_level']}")
