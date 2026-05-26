"""
Lateral movement simulation helpers.
"""
from __future__ import annotations

from typing import Any


def identify_pivot_paths(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Identify internal pivot opportunities from graph-visible nodes."""
    pivots: list[dict[str, Any]] = []
    for node in nodes:
        exposure_score = float(node.get("exposure_score") or 0.0)
        trust_score = float(node.get("trust_score") or 0.0)
        if exposure_score >= 0.5 or trust_score >= 0.5:
            pivots.append(
                {
                    "asset_id": node.get("asset_id"),
                    "hostname": node.get("hostname"),
                    "pivot_score": round(min(1.0, exposure_score + trust_score), 3),
                    "reason": node.get("reason") or "Internal adjacency and trust make pivot plausible.",
                }
            )
    return sorted(pivots, key=lambda item: item.get("pivot_score", 0.0), reverse=True)


def simulate_lateral_movement(path: dict[str, Any]) -> dict[str, Any]:
    """Simulate bounded lateral movement along a sanitized path payload."""
    pivots = identify_pivot_paths(path.get("internal_nodes", []))
    movement_score = min(
        10.0,
        float(path.get("initial_access_score") or 0.0)
        + sum(float(pivot.get("pivot_score") or 0.0) for pivot in pivots)
        + float(path.get("credential_reuse_score") or 0.0),
    )
    return {
        "asset": path.get("asset"),
        "pivot_paths": pivots,
        "movement_score": round(movement_score, 2),
        "severity": "critical" if movement_score >= 8.5 else "high" if movement_score >= 6.0 else "medium",
        "summary": f"Simulated lateral movement across {len(pivots)} pivot opportunities.",
    }


def correlate_internal_assets(assets: list[dict[str, Any]]) -> dict[str, Any]:
    """Correlate internal asset adjacency for movement planning."""
    sensitive_assets = [asset for asset in assets if asset.get("criticality") in {"critical", "high"}]
    admin_assets = [asset for asset in assets if asset.get("role") in {"admin", "control_plane", "identity"}]
    return {
        "asset_count": len(assets),
        "sensitive_assets": sensitive_assets,
        "admin_assets": admin_assets,
        "correlation_strength": round(min(1.0, (len(sensitive_assets) * 0.2) + (len(admin_assets) * 0.25)), 3),
        "summary": f"{len(sensitive_assets)} sensitive and {len(admin_assets)} administrative internal assets correlated.",
    }