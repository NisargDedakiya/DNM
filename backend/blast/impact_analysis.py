"""
Business and severity impact analysis helpers.
"""
from __future__ import annotations

from typing import Any


def analyze_business_impact(impact_context: dict[str, Any]) -> dict[str, Any]:
    """Reason about business impact from attack-path impact context."""
    critical_assets = [asset for asset in impact_context.get("affected_assets", []) if asset.get("criticality") in {"critical", "high"}]
    business_units = sorted({asset.get("business_unit") for asset in impact_context.get("affected_assets", []) if asset.get("business_unit")})
    score = min(10.0, float(impact_context.get("impact_score") or 0.0) + len(critical_assets) * 0.5 + len(business_units) * 0.25)
    return {
        "business_units": business_units,
        "critical_assets": critical_assets,
        "business_impact_score": round(score, 2),
        "severity": "critical" if score >= 8.5 else "high" if score >= 6.5 else "medium" if score >= 4.0 else "low",
        "summary": f"Business impact spans {len(business_units)} units and {len(critical_assets)} critical assets.",
    }


def propagate_severity(chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Propagate severity forward through a chain."""
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    propagated: list[dict[str, Any]] = []
    inherited = 0
    for item in chain:
        inherited = max(inherited, severity_rank.get(str(item.get("severity") or "low"), 0))
        propagated.append({**item, "propagated_severity": inherited})
    return propagated


def identify_chain_amplification(chain: list[dict[str, Any]]) -> dict[str, Any]:
    """Identify where severity or exploitability amplifies across the path."""
    amplified = [item for item in chain if float(item.get("exploitability_score") or 0.0) >= 6.0 or str(item.get("severity") or "").lower() in {"high", "critical"}]
    return {
        "amplified_nodes": amplified,
        "amplification_score": round(min(10.0, len(amplified) * 1.5), 2),
        "summary": f"Detected amplification at {len(amplified)} chain nodes.",
    }