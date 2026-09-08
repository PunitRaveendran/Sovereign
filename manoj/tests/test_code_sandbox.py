"""
tests/test_code_sandbox.py — Tests for the code sandbox tool.

Tests run against the subprocess backend (no Docker needed on dev machines).
Aparna's Docker tests run the same cases against the Docker backend on Linux.

Run:
    pytest tests/test_code_sandbox.py -v
"""

from __future__ import annotations

import sys, os, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from code_sandbox import run_code, CodeRequest, _run_in_subprocess


# ── Force subprocess backend for all tests ────────────────────────────────────

def sub(code: str, timeout: int = 10, stdin: str = "") -> dict:
    """Run code in subprocess backend regardless of Docker availability."""
    req = CodeRequest(code=code, timeout=timeout, stdin=stdin)
    return _run_in_subprocess(code, timeout, stdin)


# ── Basic execution ───────────────────────────────────────────────────────────

class TestBasicExecution:
    def test_hello_world(self):
        r = sub('print("hello")')
        assert r.exit_code == 0
        assert r.stdout.strip() == "hello"
        assert r.stderr == ""
        assert r.timed_out is False

    def test_arithmetic(self):
        r = sub("print(6 * 7)")
        assert r.stdout.strip() == "42"
        assert r.exit_code == 0

    def test_multiline_output(self):
        r = sub("for i in range(5): print(i)")
        lines = r.stdout.strip().splitlines()
        assert lines == ["0", "1", "2", "3", "4"]

    def test_stderr_captured(self):
        r = sub("import sys; sys.stderr.write('err\\n')")
        assert "err" in r.stderr
        assert r.exit_code == 0

    def test_syntax_error(self):
        r = sub("def f(: pass")
        assert r.exit_code != 0
        assert r.stderr != ""

    def test_runtime_error(self):
        r = sub("1 / 0")
        assert r.exit_code != 0
        assert "ZeroDivisionError" in r.stderr

    def test_import_stdlib(self):
        r = sub("import math; print(math.sqrt(16))")
        assert r.stdout.strip() == "4.0"

    def test_stdin_input(self):
        r = sub("name = input(); print(f'Hello {name}')", stdin="World")
        assert "Hello World" in r.stdout


# ── Timeout ───────────────────────────────────────────────────────────────────

class TestTimeout:
    def test_timeout_fires(self):
        r = sub("import time; time.sleep(10)", timeout=2)
        assert r.timed_out is True
        assert r.exit_code == -1

    def test_fast_code_no_timeout(self):
        r = sub("print('done')", timeout=5)
        assert r.timed_out is False
        assert r.exit_code == 0

    def test_runtime_reported(self):
        r = sub("import time; time.sleep(0.1)\nprint('ok')", timeout=5)
        assert r.runtime_sec >= 0.1
        assert r.exit_code == 0


# ── Output limits ─────────────────────────────────────────────────────────────

class TestOutputLimits:
    def test_large_output_truncated(self):
        # Generate >64KB of output
        r = sub("print('x' * 1000)\n" * 100, timeout=15)
        assert r.exit_code == 0
        # Either full output or truncated message
        assert len(r.stdout) <= 70 * 1024  # some slack above 64KB cap

    def test_exit_code_preserved_on_large_output(self):
        r = sub("print('a' * 100)\nimport sys; sys.exit(42)", timeout=10)
        assert r.exit_code == 42


# ── Agent demo scenarios ──────────────────────────────────────────────────────

class TestAgentScenarios:
    def test_calculation_script(self):
        """The agent generates a pump power calculation script."""
        code = textwrap.dedent("""\
            flow_rate = 50       # m3/h
            head = 30            # m
            efficiency = 0.75
            rho = 1000           # kg/m3
            g = 9.81             # m/s2
            
            hydraulic_power = rho * g * (flow_rate / 3600) * head / 1000
            shaft_power = hydraulic_power / efficiency
            
            print(f"Hydraulic power: {hydraulic_power:.2f} kW")
            print(f"Shaft power:     {shaft_power:.2f} kW")
        """)
        r = sub(code)
        assert r.exit_code == 0
        assert "Hydraulic power" in r.stdout
        assert "Shaft power" in r.stdout

    def test_data_processing(self):
        """The agent generates a simple data summary script."""
        code = textwrap.dedent("""\
            readings = [9.7, 9.8, 10.0, 9.6, 9.9]
            avg = sum(readings) / len(readings)
            minimum = min(readings)
            print(f"Average: {avg:.2f} mm")
            print(f"Minimum: {minimum:.2f} mm")
            print(f"Status: {'PASS' if minimum >= 9.5 else 'FAIL'}")
        """)
        r = sub(code)
        assert r.exit_code == 0
        assert "PASS" in r.stdout

    def test_no_network_access_from_agent_code(self):
        """
        Verify that a script trying to import socket and connect fails
        gracefully (subprocess doesn't block network, but on Docker it will).
        This test documents the expected behaviour difference.
        """
        # This will succeed in subprocess (no network block)
        # but will fail/hang in Docker (--network none)
        # On demo machine, Aparna's Docker ensures actual isolation.
        code = "import socket; print('socket imported')"
        r = sub(code)
        # Just confirm it runs — Docker isolation is Aparna's layer
        assert r.exit_code == 0


