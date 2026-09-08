"""
rbac.py — Role-Based Access Control (data-layer enforcement).

Rules:
  - Access is enforced BEFORE data reaches the model — the model never sees
    what it isn't allowed to.
  - Tags are assigned at ingestion, not at query time.
  - Every access attempt is logged to the audit log.

Access levels (lowest → highest):
    public      → all roles
    department  → dept. lead, management, VP/CEO
    management  → management, VP/CEO
    executive   → VP/CEO only

Role definitions are in ROLE_PERMISSIONS below. Rahul owns the matrix
definition and test cases — just update the dict and re-run tests.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Sequence

from loguru import logger


# ── Enums ─────────────────────────────────────────────────────────────────────

class AccessLevel(str, Enum):
    PUBLIC     = "public"
    DEPARTMENT = "department"
    MANAGEMENT = "management"
    EXECUTIVE  = "executive"

    # Ordered list for comparison
    _order = None  # populated below

    def __lt__(self, other: "AccessLevel") -> bool:
        return _LEVEL_ORDER.index(self) < _LEVEL_ORDER.index(other)

    def __le__(self, other: "AccessLevel") -> bool:
        return _LEVEL_ORDER.index(self) <= _LEVEL_ORDER.index(other)


_LEVEL_ORDER: list[AccessLevel] = [
    AccessLevel.PUBLIC,
    AccessLevel.DEPARTMENT,
    AccessLevel.MANAGEMENT,
    AccessLevel.EXECUTIVE,
]


class Role(str, Enum):
    WEB_DEV          = "web_dev"
    DEPARTMENT_LEAD  = "department_lead"
    MANAGEMENT       = "management"
    VP_CEO           = "vp_ceo"


# ── Role → allowed access levels matrix ───────────────────────────────────────
# Rahul: adjust this matrix and add test cases that verify the boundaries.
ROLE_PERMISSIONS: dict[Role, list[AccessLevel]] = {
    Role.WEB_DEV: [
        AccessLevel.PUBLIC,
    ],
    Role.DEPARTMENT_LEAD: [
        AccessLevel.PUBLIC,
        AccessLevel.DEPARTMENT,
    ],
    Role.MANAGEMENT: [
        AccessLevel.PUBLIC,
        AccessLevel.DEPARTMENT,
        AccessLevel.MANAGEMENT,
    ],
    Role.VP_CEO: [
        AccessLevel.PUBLIC,
        AccessLevel.DEPARTMENT,
        AccessLevel.MANAGEMENT,
        AccessLevel.EXECUTIVE,
    ],
}


# ── Audit log ─────────────────────────────────────────────────────────────────

class AuditLogger:
    """Append-only local audit log for every access attempt (granted + denied)."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, record: dict) -> None:
        line = json.dumps(record, default=str)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        logger.debug("AUDIT | {}", line)

    def log_access(
        self,
        *,
        user: str,
        role: Role,
        resource: str,
        requested_level: AccessLevel,
        granted: bool,
        reason: str = "",
    ) -> None:
        self._write(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "user": user,
                "role": role,
                "resource": resource,
                "requested_level": requested_level,
                "granted": granted,
                "reason": reason,
            }
        )

    def read_recent(self, n: int = 50) -> list[dict]:
        """Return the last *n* audit records (for the dashboard)."""
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(l) for l in lines[-n:]]


# ── RBAC gate ─────────────────────────────────────────────────────────────────

class RBACGate:
    """
    Central enforcement point.  Every tool call and retrieval query must pass
    through this gate BEFORE data is accessed.
    """

    def __init__(self, audit_logger: AuditLogger) -> None:
        self.audit = audit_logger

    def allowed_levels(self, role: Role) -> list[AccessLevel]:
        return ROLE_PERMISSIONS.get(role, [AccessLevel.PUBLIC])

    def check(
        self,
        *,
        user: str,
        role: Role,
        resource: str,
        required_level: AccessLevel,
    ) -> bool:
        """
        Returns True if *role* may access *resource* tagged at *required_level*.
        Logs every check to the audit log regardless of outcome.
        """
        permitted = required_level in self.allowed_levels(role)
        self.audit.log_access(
            user=user,
            role=role,
            resource=resource,
            requested_level=required_level,
            granted=permitted,
            reason="" if permitted else f"Role '{role}' cannot access level '{required_level}'",
        )
        return permitted

    def chroma_filter(self, role: Role) -> dict:
        """
        Build a Chroma `where` metadata filter that restricts results to
        access levels the role is allowed to see.
        Used by the KB search tool for hard retrieval-side enforcement.
        """
        levels = [lvl.value for lvl in self.allowed_levels(role)]
        return {"access_level": {"$in": levels}}

    def assert_access(
        self,
        *,
        user: str,
        role: Role,
        resource: str,
        required_level: AccessLevel,
    ) -> None:
        """Raise PermissionError if access is denied (for tool-call gates)."""
        if not self.check(user=user, role=role, resource=resource, required_level=required_level):
            raise PermissionError(
                f"Access denied: user='{user}' role='{role}' "
                f"cannot access '{resource}' (level={required_level})"
            )


# ── Convenience singleton builders ────────────────────────────────────────────

def build_rbac(audit_log_path: Path) -> tuple[RBACGate, AuditLogger]:
    audit = AuditLogger(audit_log_path)
    gate  = RBACGate(audit)
    return gate, audit
