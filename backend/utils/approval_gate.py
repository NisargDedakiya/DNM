"""
Human approval gate for scan execution safety.

Blocks dangerous or sensitive scan workflows unless explicit approval is present.
"""
from __future__ import annotations

from typing import Any


HIGH_RISK_SCANNERS = {
    "sqlmap",
    "ffuf",
    "wfuzz",
}

APPROVAL_REQUIRED_FLAGS = {
    "authenticated_scan",
    "aggressive_fuzzing",
    "high_depth_crawling",
}


def classify_scan_risk(
    scanner_name: str,
    *,
    authenticated_scan: bool = False,
    aggressive_fuzzing: bool = False,
    crawl_depth: int = 1,
    target_count: int = 1,
) -> dict[str, Any]:
    """Classify scan risk for policy enforcement."""
    scanner = (scanner_name or "").strip().lower()

    risk_score = 0
    reasons: list[str] = []

    if scanner in HIGH_RISK_SCANNERS:
        risk_score += 45
        reasons.append(f"high_risk_scanner:{scanner}")

    if authenticated_scan:
        risk_score += 20
        reasons.append("authenticated_scan")

    if aggressive_fuzzing:
        risk_score += 20
        reasons.append("aggressive_fuzzing")

    if crawl_depth >= 4:
        risk_score += 20
        reasons.append(f"high_depth_crawling:{crawl_depth}")

    if target_count >= 50:
        risk_score += 15
        reasons.append(f"wide_target_surface:{target_count}")

    if risk_score >= 70:
        level = "critical"
    elif risk_score >= 45:
        level = "high"
    elif risk_score >= 20:
        level = "medium"
    else:
        level = "low"

    requires_manual_approval = (
        scanner in HIGH_RISK_SCANNERS
        or authenticated_scan
        or aggressive_fuzzing
        or crawl_depth >= 4
    )

    return {
        "risk_level": level,
        "risk_score": risk_score,
        "requires_manual_approval": requires_manual_approval,
        "reasons": reasons,
    }


def require_manual_approval(
    *,
    approved_by_human: bool,
    risk_profile: dict[str, Any],
) -> dict[str, Any]:
    """Enforce manual approval for high-risk scan profiles."""
    required = bool(risk_profile.get("requires_manual_approval", False))

    if required and not approved_by_human:
        return {
            "allowed": False,
            "reason": "manual_approval_required",
            "risk_profile": risk_profile,
        }

    return {
        "allowed": True,
        "reason": "approved" if approved_by_human else "not_required",
        "risk_profile": risk_profile,
    }


def validate_scan_execution(
    *,
    scanner_name: str,
    approved_by_human: bool,
    authenticated_scan: bool = False,
    aggressive_fuzzing: bool = False,
    crawl_depth: int = 1,
    target_count: int = 1,
    within_scope: bool = False,
) -> dict[str, Any]:
    """Final pre-execution policy decision for scan authorization."""
    if not within_scope:
        return {
            "allowed": False,
            "reason": "target_out_of_scope",
            "risk_profile": None,
        }

    risk_profile = classify_scan_risk(
        scanner_name,
        authenticated_scan=authenticated_scan,
        aggressive_fuzzing=aggressive_fuzzing,
        crawl_depth=crawl_depth,
        target_count=target_count,
    )

    approval = require_manual_approval(
        approved_by_human=approved_by_human,
        risk_profile=risk_profile,
    )

    if not approval["allowed"]:
        return {
            "allowed": False,
            "reason": approval["reason"],
            "risk_profile": risk_profile,
        }

    return {
        "allowed": True,
        "reason": "execution_authorized",
        "risk_profile": risk_profile,
    }
