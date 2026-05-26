"""
Trust boundary analysis helpers.
"""
from __future__ import annotations

from typing import Any


def analyze_trust_boundary(boundaries: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze trust relationships between identities, tokens, and services."""
    weak_boundaries = [boundary for boundary in boundaries if float(boundary.get("trust_score") or 0.0) >= 0.6]
    auth_flows = [boundary.get("auth_flow") for boundary in boundaries if boundary.get("auth_flow")]
    return {
        "boundary_count": len(boundaries),
        "weak_boundaries": weak_boundaries,
        "auth_flows": auth_flows,
        "severity": "high" if weak_boundaries else "low",
        "summary": f"Evaluated {len(boundaries)} trust boundaries and found {len(weak_boundaries)} weak segments.",
    }


def identify_trust_violations(boundary_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract potential trust violations from the analysis payload."""
    violations: list[dict[str, Any]] = []
    for boundary in boundary_analysis.get("weak_boundaries", []):
        violations.append(
            {
                "source": boundary.get("source"),
                "target": boundary.get("target"),
                "violation_type": boundary.get("violation_type") or "overbroad_trust",
                "severity": boundary.get("severity") or "high",
            }
        )
    return violations


def correlate_boundary_exposure(boundaries: list[dict[str, Any]]) -> dict[str, Any]:
    """Correlate trust boundary exposure into a single summary."""
    analysis = analyze_trust_boundary(boundaries)
    violations = identify_trust_violations(analysis)
    return {
        **analysis,
        "violations": violations,
        "boundary_risk": round(min(10.0, len(violations) * 2.0 + len(analysis.get("auth_flows", [])) * 0.5), 2),
    }