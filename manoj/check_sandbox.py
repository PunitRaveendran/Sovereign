"""
Live check for the code sandbox endpoint.
Runs 5 real test cases against the running server.
"""
import httpx, json

client = httpx.Client(timeout=60, base_url="http://127.0.0.1:8001")

SEP = "-" * 55

def post(code, timeout=10, stdin=""):
    r = client.post("/tools/run_code", json={"code": code, "timeout": timeout, "stdin": stdin})
    return r.json()

# ── 1. Sandbox info ─────────────────────────────────────────────────────────
print(SEP)
info = client.get("/tools/sandbox_info").json()
print(f"[INFO] Active backend : {info['active_backend']}")
print(f"       Docker avail   : {info['docker_available']}")
print(f"       Network isolated: {info['network_isolated']}")
print(f"       Note: {info['note'][:70]}")

# ── 2. Hello world ───────────────────────────────────────────────────────────
print(SEP)
r = post('print("Hello from Sovereign sandbox!")')
print(f"[TEST 1] Hello world")
print(f"  exit_code : {r['exit_code']}")
print(f"  stdout    : {r['stdout'].strip()}")
print(f"  backend   : {r['backend']}")
print(f"  runtime   : {r['runtime_sec']}s")

# ── 3. Pump power calculation (agent demo scenario) ───────────────────────────
print(SEP)
calc_code = """
flow_rate  = 50        # m3/h
head       = 30        # m
efficiency = 0.75
rho = 1000; g = 9.81

hydraulic_kw = rho * g * (flow_rate / 3600) * head / 1000
shaft_kw     = hydraulic_kw / efficiency

print(f"Hydraulic power : {hydraulic_kw:.2f} kW")
print(f"Shaft power     : {shaft_kw:.2f} kW")
print(f"Status          : {'PASS' if shaft_kw < 10 else 'REVIEW'}")
"""
r = post(calc_code)
print(f"[TEST 2] Pump power calculation")
print(f"  exit_code : {r['exit_code']}")
for line in r["stdout"].strip().splitlines():
    print(f"  {line}")

# ── 4. Error handling (bad code) ─────────────────────────────────────────────
print(SEP)
r = post("x = 1 / 0")
print(f"[TEST 3] Runtime error (1/0)")
print(f"  exit_code : {r['exit_code']}  (expected: non-zero)")
print(f"  stderr    : {r['stderr'].strip().splitlines()[-1]}")

# ── 5. Timeout enforcement ────────────────────────────────────────────────────
print(SEP)
r = post("import time; time.sleep(10)", timeout=2)
print(f"[TEST 4] Timeout (sleep 10s, limit 2s)")
print(f"  timed_out : {r['timed_out']}  (expected: True)")
print(f"  error     : {r['error']}")

# ── 6. Sandbox health endpoint ────────────────────────────────────────────────
print(SEP)
health = client.get("/tools/sandbox_health").json()
print(f"[TEST 5] Sandbox self-test (print(1+1))")
print(f"  status  : {health['status']}  (expected: ok)")
print(f"  output  : {health['output']}  (expected: 2)")
print(f"  backend : {health['backend']}")

print(SEP)
print("All sandbox checks complete.")
