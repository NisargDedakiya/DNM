"""
Blast radius calculation helpers.
"""
from __future__ import annotations

from typing import Any


def calculate_blast_radius(paths: list[dict[str, Any]], assets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Calculate attack impact from reachable path data."""
    assets = assets or []
    impact_score = min(
        10.0,
        sum(float(path.get("exploitability_score") or 0.0) for path in paths) * 0.5 + len(assets) * 0.25,
    )
    affected_assets = sorted(
        {str(asset.get("hostname") or asset.get("asset_id") or asset.get("id") or "unknown") for asset in assets}
    )
    return {
        "affected_assets": affected_assets,
        "impact_score": round(impact_score, 2),
        "severity": "critical" if impact_score >= 8.5 else "high" if impact_score >= 6.5 else "medium" if impact_score >= 4.0 else "low",
        "summary": f"Blast radius spans {len(affected_assets)} assets across {len(paths)} paths.",
    }


def analyze_asset_impact(asset: dict[str, Any], dependencies: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Analyze how a single asset contributes to propagation."""
    dependencies = dependencies or []
    propagation = min(10.0, float(asset.get("criticality_score") or 0.0) + len(dependencies) * 0.8)
    return {
        "asset": {"id": asset.get("id"), "hostname": asset.get("hostname")},
        "dependency_count": len(dependencies),
        "propagation_score": round(propagation, 2),
        "severity": "critical" if propagation >= 8.5 else "high" if propagation >= 6.0 else "medium",
    }


def prioritize_high_impact_paths(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank paths by their calculated impact."""
    return sorted(
        paths,
        key=lambda item: (
            float(item.get("impact_score") or item.get("exploitability_score") or 0.0),
            len(item.get("affected_assets", [])),
        ),
        reverse=True,
    )