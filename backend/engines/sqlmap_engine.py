"""
Approval-gated SQLMap engine with strict safety controls.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from backend.scanners.base_scanner import BaseScanner
from backend.utils.approval_gate import validate_scan_execution
from backend.utils.scope_validator import validate_target


class _SqlmapRunner(BaseScanner):
    def validate_target(self, target: str) -> bool:
        return bool(re.match(r"^https?://[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$", target.strip()))

    async def run(self, target: str) -> dict[str, Any]:
        raise NotImplementedError("Use run_sqlmap_scan")

    def parse_output(self, output: str) -> list[str]:
        return [line for line in output.splitlines() if line.strip()]


def validate_sqlmap_approval(
    *,
    target: str,
    scope_rules: list[str],
    approval_token: str | None,
    approved_by_human: bool,
) -> dict[str, Any]:
    """Validate strict approval and scope prerequisites for sqlmap execution."""
    scope_check = validate_target(target, scope_rules)
    if not scope_check["authorized"]:
        return {"allowed": False, "reason": "target_out_of_scope", "audit": scope_check}

    if not approval_token or len(approval_token.strip()) < 8:
        return {"allowed": False, "reason": "missing_or_invalid_approval_token", "audit": scope_check}

    policy = validate_scan_execution(
        scanner_name="sqlmap",
        approved_by_human=approved_by_human,
        authenticated_scan=False,
        aggressive_fuzzing=False,
        crawl_depth=1,
        target_count=1,
        within_scope=True,
    )
    if not policy["allowed"]:
        return {"allowed": False, "reason": policy["reason"], "audit": scope_check}

    return {"allowed": True, "reason": "approved", "audit": scope_check}


async def run_sqlmap_scan(
    *,
    target: str,
    scope_rules: list[str],
    approval_token: str | None,
    approved_by_human: bool,
    timeout: int = 180,
) -> dict[str, Any]:
    """Run sqlmap in a constrained verification mode only after explicit approval."""
    approval = validate_sqlmap_approval(
        target=target,
        scope_rules=scope_rules,
        approval_token=approval_token,
        approved_by_human=approved_by_human,
    )
    if not approval["allowed"]:
        return {
            "scanner": "sqlmap",
            "status": "blocked",
            "reason": approval["reason"],
            "audit": {
                **approval.get("audit", {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    runner = _SqlmapRunner(timeout=timeout)
    safe_target = target.strip()

    # Safe verification mode: non-destructive and limited.
    cmd = [
        "sqlmap",
        "-u",
        safe_target,
        "--batch",
        "--risk",
        "1",
        "--level",
        "1",
        "--technique",
        "B",
        "--threads",
        "1",
        "--timeout",
        "10",
        "--answers",
        "follow=Y",
    ]

    try:
        stdout, stderr = await runner.execute_subprocess(cmd)
        return {
            "scanner": "sqlmap",
            "status": "completed",
            "target": safe_target,
            "output": runner.parse_output(stdout),
            "stderr": stderr,
            "audit": {
                **approval.get("audit", {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "approved": True,
            },
        }
    except Exception as exc:
        return {
            "scanner": "sqlmap",
            "status": "failed",
            "target": safe_target,
            "error": str(exc),
            "audit": {
                **approval.get("audit", {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "approved": True,
            },
        }
