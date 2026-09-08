"""
tests/test_rbac.py — RBAC test suite (Rahul's responsibility for test cases).

These tests validate that the access control boundary holds:
  - A web-dev role NEVER surfaces executive or management content.
  - A VP/CEO role CAN access everything.
  - Audit log records every attempt.

Run:
    pytest tests/test_rbac.py -v
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
import tempfile
import pytest

from rbac import (
    AccessLevel, Role, RBACGate, AuditLogger, ROLE_PERMISSIONS, build_rbac
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def audit_log(tmp_path: Path):
    return AuditLogger(tmp_path / "audit.log")


@pytest.fixture
def gate(audit_log):
    return RBACGate(audit_log)


# ── Role permission matrix tests ───────────────────────────────────────────────

class TestRoleMatrix:
    def test_web_dev_only_sees_public(self, gate):
        levels = gate.allowed_levels(Role.WEB_DEV)
        assert AccessLevel.PUBLIC in levels
        assert AccessLevel.DEPARTMENT not in levels
        assert AccessLevel.MANAGEMENT not in levels
        assert AccessLevel.EXECUTIVE not in levels

    def test_dept_lead_sees_public_and_department(self, gate):
        levels = gate.allowed_levels(Role.DEPARTMENT_LEAD)
        assert AccessLevel.PUBLIC in levels
        assert AccessLevel.DEPARTMENT in levels
        assert AccessLevel.MANAGEMENT not in levels
        assert AccessLevel.EXECUTIVE not in levels

    def test_management_sees_up_to_management(self, gate):
        levels = gate.allowed_levels(Role.MANAGEMENT)
        assert AccessLevel.PUBLIC in levels
        assert AccessLevel.DEPARTMENT in levels
        assert AccessLevel.MANAGEMENT in levels
        assert AccessLevel.EXECUTIVE not in levels

    def test_vp_ceo_sees_all(self, gate):
        levels = gate.allowed_levels(Role.VP_CEO)
        from rbac import _LEVEL_ORDER
        assert all(lvl in levels for lvl in _LEVEL_ORDER)


# ── check() and assert_access() tests ─────────────────────────────────────────

class TestGateCheck:
    def test_web_dev_denied_executive(self, gate):
        result = gate.check(
            user="alice", role=Role.WEB_DEV,
            resource="exec_report.pdf", required_level=AccessLevel.EXECUTIVE,
        )
        assert result is False

    def test_web_dev_denied_management(self, gate):
        result = gate.check(
            user="alice", role=Role.WEB_DEV,
            resource="mgmt_notes.docx", required_level=AccessLevel.MANAGEMENT,
        )
        assert result is False

    def test_web_dev_denied_department(self, gate):
        result = gate.check(
            user="alice", role=Role.WEB_DEV,
            resource="dept_report.pdf", required_level=AccessLevel.DEPARTMENT,
        )
        assert result is False

    def test_web_dev_allowed_public(self, gate):
        result = gate.check(
            user="alice", role=Role.WEB_DEV,
            resource="sop.pdf", required_level=AccessLevel.PUBLIC,
        )
        assert result is True

    def test_vp_allowed_executive(self, gate):
        result = gate.check(
            user="bob", role=Role.VP_CEO,
            resource="vendor_strategy.pdf", required_level=AccessLevel.EXECUTIVE,
        )
        assert result is True

    def test_assert_access_raises_on_denial(self, gate):
        with pytest.raises(PermissionError, match="Access denied"):
            gate.assert_access(
                user="charlie", role=Role.WEB_DEV,
                resource="executive_briefing.pdf",
                required_level=AccessLevel.EXECUTIVE,
            )

    def test_assert_access_no_raise_on_permit(self, gate):
        # Should not raise
        gate.assert_access(
            user="dave", role=Role.VP_CEO,
            resource="executive_briefing.pdf",
            required_level=AccessLevel.EXECUTIVE,
        )


# ── Chroma filter tests ───────────────────────────────────────────────────────

class TestChromaFilter:
    def test_web_dev_filter_only_public(self, gate):
        f = gate.chroma_filter(Role.WEB_DEV)
        assert f == {"access_level": {"$in": ["public"]}}

    def test_vp_filter_includes_all(self, gate):
        f = gate.chroma_filter(Role.VP_CEO)
        levels = set(f["access_level"]["$in"])
        assert levels == {"public", "department", "management", "executive"}

    def test_dept_lead_filter(self, gate):
        f = gate.chroma_filter(Role.DEPARTMENT_LEAD)
        assert set(f["access_level"]["$in"]) == {"public", "department"}


# ── Audit log tests ───────────────────────────────────────────────────────────

class TestAuditLog:
    def test_audit_log_records_denial(self, gate, audit_log):
        gate.check(
            user="eve", role=Role.WEB_DEV,
            resource="exec_file.pdf", required_level=AccessLevel.EXECUTIVE,
        )
        records = audit_log.read_recent(10)
        assert len(records) == 1
        assert records[0]["granted"] is False
        assert records[0]["user"] == "eve"
        assert records[0]["requested_level"] == "executive"

    def test_audit_log_records_grant(self, gate, audit_log):
        gate.check(
            user="frank", role=Role.VP_CEO,
            resource="exec_file.pdf", required_level=AccessLevel.EXECUTIVE,
        )
        records = audit_log.read_recent(10)
        assert records[0]["granted"] is True

    def test_audit_log_captures_both_attempts(self, gate, audit_log):
        # Web dev denied
        gate.check(user="alice", role=Role.WEB_DEV, resource="r", required_level=AccessLevel.EXECUTIVE)
        # VP allowed (same resource)
        gate.check(user="bob",   role=Role.VP_CEO,  resource="r", required_level=AccessLevel.EXECUTIVE)
        records = audit_log.read_recent(10)
        assert len(records) == 2
        assert records[0]["granted"] is False
        assert records[1]["granted"] is True


# ── Demo path: the RBAC live demo described in section 3 ─────────────────────

class TestLiveDemoPath:
    """
    Simulates the live demo: log in as web_dev, ask for restricted content
    → denied. Log in as vp_ceo, ask same → granted. Show audit log.

    This is Rahul's test to write and run before the demo.
    """

    def test_demo_web_dev_cannot_see_vendor_strategy(self, gate, audit_log):
        """Web dev asking about Q3 vendor negotiation strategy → should be denied."""
        resource = "executive_vendor_strategy_Q3.txt"
        result = gate.check(
            user="rahul_webdev",
            role=Role.WEB_DEV,
            resource=resource,
            required_level=AccessLevel.EXECUTIVE,
        )
        assert result is False, "Web dev should NOT see executive content"

    def test_demo_vp_can_see_vendor_strategy(self, gate, audit_log):
        """VP asking about Q3 vendor negotiation strategy → should be granted."""
        resource = "executive_vendor_strategy_Q3.txt"
        result = gate.check(
            user="punit_vp",
            role=Role.VP_CEO,
            resource=resource,
            required_level=AccessLevel.EXECUTIVE,
        )
        assert result is True, "VP should see executive content"

    def test_demo_audit_log_shows_both(self, gate, audit_log):
        """After both attempts, audit log should record denial then grant."""
        resource = "executive_vendor_strategy_Q3.txt"
        gate.check(user="rahul_webdev", role=Role.WEB_DEV, resource=resource,
                   required_level=AccessLevel.EXECUTIVE)
        gate.check(user="punit_vp",     role=Role.VP_CEO,  resource=resource,
                   required_level=AccessLevel.EXECUTIVE)
        records = audit_log.read_recent(10)
        assert len(records) == 2
        denied = [r for r in records if not r["granted"]]
        granted = [r for r in records if r["granted"]]
        assert len(denied) == 1
        assert len(granted) == 1
        assert denied[0]["user"] == "rahul_webdev"
        assert granted[0]["user"] == "punit_vp"
