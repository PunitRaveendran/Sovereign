"""
airgap_verify.py — Air-gap sovereignty verification tool.

Runs a series of checks and produces a printable verification report:
  1. Network interface status (is Wi-Fi/Ethernet up?)
  2. Active connections (anything talking externally?)
  3. iptables OUTPUT rules (are egress rules in place?)
  4. Docker network check (are containers isolated?)
  5. Sovereign services health (KB, doc-gen, network monitor alive?)
  6. Live network monitor reading (packets_sent = 0?)

Run before the demo to confirm the machine is truly air-gapped.
Output is also saved to airgap_report.txt for the audit log.

Usage:
    python airgap/airgap_verify.py
    python airgap/airgap_verify.py --host 127.0.0.1 --port 8001
"""

from __future__ import annotations

import json
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1252 codec errors)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import httpx
import psutil

# ── Config ─────────────────────────────────────────────────────────────────────
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001
REPORT_PATH  = Path(__file__).parent.parent / "airgap_report.txt"
EXTERNAL_TEST_HOSTS = ["8.8.8.8", "1.1.1.1", "google.com"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def section(title: str) -> None:
    print(f"\n{'-'*60}")
    print(f"  {title}")
    print(f"{'-'*60}")


def ok(msg: str) -> str:
    print(f"  [PASS] {msg}")
    return f"PASS | {msg}"


def fail(msg: str) -> str:
    print(f"  [FAIL] {msg}")
    return f"FAIL | {msg}"


def warn(msg: str) -> str:
    print(f"  [WARN] {msg}")
    return f"WARN | {msg}"


def info(msg: str) -> str:
    print(f"         {msg}")
    return f"INFO | {msg}"


# ── Checks ────────────────────────────────────────────────────────────────────

def check_network_interfaces() -> list[str]:
    results = []
    section("1. Network Interface Status")
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    suspicious = []
    for iface, stat in stats.items():
        is_up = stat.isup
        is_loopback = iface.lower() in ("lo", "loopback")
        addr_list = [a.address for a in addrs.get(iface, [])]
        addr_str = ", ".join(addr_list) or "no address"
        msg = f"{iface}: {'UP' if is_up else 'DOWN'} | {addr_str}"
        if is_up and not is_loopback:
            suspicious.append(iface)
            results.append(warn(msg + " ← external interface is UP"))
        else:
            results.append(info(msg))

    if not suspicious:
        results.append(ok("No external network interfaces are up"))
    else:
        results.append(fail(f"External interfaces still up: {suspicious}"))
    return results


def check_external_connectivity() -> list[str]:
    results = []
    section("2. External Connectivity Test")
    any_reachable = False
    for host in EXTERNAL_TEST_HOSTS:
        try:
            sock = socket.create_connection((host, 80), timeout=2)
            sock.close()
            results.append(fail(f"Reached {host}:80 — machine is NOT air-gapped!"))
            any_reachable = True
        except (socket.timeout, OSError):
            results.append(ok(f"Cannot reach {host} (connection refused/timed out)"))
    if not any_reachable:
        results.append(ok("All external connectivity tests failed as expected"))
    return results


def check_active_connections() -> list[str]:
    results = []
    section("3. Active Network Connections")
    conns = psutil.net_connections(kind="inet")
    external = [
        c for c in conns
        if c.raddr and not c.raddr.ip.startswith("127.")
        and c.raddr.ip not in ("0.0.0.0", "::")
        and c.status == "ESTABLISHED"
    ]
    if external:
        for c in external:
            results.append(fail(f"External connection: {c.laddr.ip}:{c.laddr.port} "
                                f"-> {c.raddr.ip}:{c.raddr.port} (pid={c.pid})"))
    else:
        results.append(ok("No established external connections found"))
    return results


def check_iptables() -> list[str]:
    results = []
    section("4. iptables Egress Rules")
    if platform.system() != "Linux":
        results.append(info("iptables check skipped on non-Linux (Windows demo machine)"))
        results.append(info("On Linux air-gap laptop: run sudo bash egress/setup_egress.sh"))
        return results
    try:
        out = subprocess.check_output(
            ["iptables", "-L", "OUTPUT", "-v", "-n", "--line-numbers"],
            stderr=subprocess.STDOUT, text=True
        )
        has_drop = "DROP" in out
        results.append(ok("iptables OUTPUT chain contains DROP rule") if has_drop
                       else fail("No DROP rule in OUTPUT chain — egress not locked!"))
        for line in out.strip().splitlines():
            results.append(info(line))
    except FileNotFoundError:
        results.append(warn("iptables not found — skipping (install iptables or use Docker)"))
    except subprocess.CalledProcessError as e:
        results.append(warn(f"iptables check failed (may need sudo): {e}"))
    return results


def check_docker_isolation() -> list[str]:
    results = []
    section("5. Docker Network Isolation")
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Networks}}"],
            stderr=subprocess.STDOUT, text=True, timeout=5
        )
        if not out.strip():
            results.append(info("No Docker containers running"))
        else:
            for line in out.strip().splitlines():
                parts = line.split("\t")
                name    = parts[0] if parts else "?"
                network = parts[1] if len(parts) > 1 else "?"
                if network in ("none", ""):
                    results.append(ok(f"Container '{name}' uses network=none (isolated)"))
                else:
                    results.append(warn(f"Container '{name}' on network '{network}' — verify isolation"))
    except FileNotFoundError:
        results.append(info("Docker not installed — skipping container check"))
    except subprocess.CalledProcessError:
        results.append(info("Docker daemon not running — skipping"))
    return results


def check_sovereign_health(host: str, port: int) -> list[str]:
    results = []
    section("6. Sovereign Services Health")
    base = f"http://{host}:{port}"
    client = httpx.Client(timeout=10)
    try:
        r = client.get(f"{base}/health")
        data = r.json()
        results.append(ok(f"API gateway reachable: status={data['status']}"))
    except Exception as e:
        results.append(fail(f"API gateway unreachable: {e}"))
        results.append(info("Make sure: python -m uvicorn main:app --port 8001"))
        return results

    try:
        r = client.get(f"{base}/kb/health")
        data = r.json()
        doc_count = data.get("doc_count", 0)
        if doc_count > 0:
            results.append(ok(f"Chroma KB healthy: {doc_count} chunks indexed"))
        else:
            results.append(fail("Chroma KB is empty — run: python demo_data.py --ingest"))
    except Exception as e:
        results.append(fail(f"KB health check failed: {e}"))

    try:
        r = client.get(f"{base}/network/stats")
        data = r.json()
        sent = data.get("packets_sent_per_sec", -1)
        if sent == 0:
            results.append(ok(f"Network monitor: packets_sent_per_sec = 0  <-- SOVEREIGNTY PROOF"))
        else:
            results.append(warn(f"Network monitor: packets_sent_per_sec = {sent} "
                                f"(expected 0 on air-gap machine)"))
    except Exception as e:
        results.append(fail(f"Network monitor check failed: {e}"))

    return results


def check_live_egress(host: str, port: int, duration: int = 5) -> list[str]:
    results = []
    section(f"7. Live Egress Monitor ({duration}s sample)")
    base = f"http://{host}:{port}"
    client = httpx.Client(timeout=10)
    samples = []
    try:
        for i in range(duration):
            r = client.get(f"{base}/network/stats")
            data = r.json()
            sent = data.get("packets_sent_per_sec", -1)
            samples.append(sent)
            print(f"  t+{i+1}s: packets_sent_per_sec = {sent}")
            time.sleep(1)
        total_sent = sum(s for s in samples if s >= 0)
        if total_sent == 0:
            results.append(ok(f"ZERO packets sent over {duration}s — machine is air-gapped"))
        else:
            results.append(fail(f"{total_sent:.1f} packets/s sent — machine has external traffic"))
    except Exception as e:
        results.append(fail(f"Live egress check failed: {e}"))
    return results


# ── Report ────────────────────────────────────────────────────────────────────

def run_all(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    print("\n" + "="*60)
    print("  SOVEREIGN — Air-Gap Verification Report")
    print(f"  Machine:  {platform.node()}")
    print(f"  OS:       {platform.system()} {platform.release()}")
    print(f"  Time:     {datetime.now(timezone.utc).isoformat()}")
    print("="*60)

    all_results: list[str] = []
    all_results += check_network_interfaces()
    all_results += check_external_connectivity()
    all_results += check_active_connections()
    all_results += check_iptables()
    all_results += check_docker_isolation()
    all_results += check_sovereign_health(host, port)
    all_results += check_live_egress(host, port)

    # Summary
    passes = sum(1 for r in all_results if r.startswith("PASS"))
    fails  = sum(1 for r in all_results if r.startswith("FAIL"))
    warns  = sum(1 for r in all_results if r.startswith("WARN"))

    print("\n" + "="*60)
    print("  SUMMARY: {} passed | {} warnings | {} failed".format(passes, warns, fails))
    if fails == 0:
        print("  STATUS:  AIR-GAP VERIFIED [OK]")
    else:
        print("  STATUS:  NOT FULLY AIR-GAPPED -- fix FAIL items above")
    print("="*60)

    # Write report to disk
    report_lines = [
        "SOVEREIGN Air-Gap Verification Report",
        f"Machine: {platform.node()}",
        f"Time:    {datetime.now(timezone.utc).isoformat()}",
        f"Summary: {passes} passed / {warns} warnings / {fails} failed",
        "",
    ] + all_results
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n  Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sovereign air-gap verification")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    run_all(args.host, args.port)
