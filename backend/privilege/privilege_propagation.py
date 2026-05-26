"""
Privilege propagation and escalation helpers.
"""
from __future__ import annotations

from typing import Any


ROLE_ORDER = {"viewer": 1, "analyst": 2, "admin": 3, "owner": 4}


def analyze_privilege_chain(chain: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze privilege transitions along a multi-step chain."""
    transitions = []
    previous_rank = 0
    for step in chain:
        role = str(step.get("role") or step.get("escalated_privilege") or "viewer").lower()
        current_rank = ROLE_ORDER.get(role, 0)
        transitions.append({**step, "role_rank": current_rank, "escalation": max(0, current_rank - previous_rank)})
        previous_rank = current_rank
    severity = "critical" if any(item["escalation"] >= 2 for item in transitions) else "high" if any(item["escalation"] == 1 for item in transitions) else "medium"
    return {
        "transitions": transitions,
        "severity": severity,
        "summary": f"Analyzed {len(transitions)} privilege transitions.",
    }


def simulate_privilege_escalation(identity: dict[str, Any], path: list[dict[str, Any]]) -> dict[str, Any]:
    """Simulate bounded privilege escalation using sanitized path data."""
    starting_role = str(identity.get("role") or "viewer").lower()
    start_rank = ROLE_ORDER.get(starting_role, 0)
    target_rank = max((ROLE_ORDER.get(str(step.get("target_role") or step.get("escalated_privilege") or "viewer").lower(), 0) for step in path), default=start_rank)
    gain = max(0, target_rank - start_rank)
    return {
        "identity": {"id": identity.get("id"), "role": starting_role},
        "target_rank": target_rank,
        "escalation_gain": gain,
        "severity": "critical" if gain >= 2 else "high" if gain == 1 else "medium",
        "summary": f"Simulated escalation gain of {gain} role levels.",
    }


def identify_permission_propagation(chain: list[dict[str, Any]]) -> dict[str, Any]:
    """Identify whether permissions propagate too broadly through the chain."""
    propagated_permissions = sorted({str(step.get("permission") or step.get("propagated_permission") or "") for step in chain if step.get("permission") or step.get("propagated_permission")})
    return {
        "permissions": propagated_permissions,
        "propagation_risk": round(min(10.0, len(propagated_permissions) * 1.2), 2),
        "severity": "high" if len(propagated_permissions) >= 3 else "medium" if propagated_permissions else "info",
        "summary": f"{len(propagated_permissions)} permissions observed across the chain.",
    }