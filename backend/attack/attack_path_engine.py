"""
Attack-path reasoning engine.
"""
from __future__ import annotations

from typing import Any


SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _severity_for_score(score: float) -> str:
    if score >= 8.5:
        return "critical"
    if score >= 6.5:
        return "high"
    if score >= 4.0:
        return "medium"
    return "low"


def build_attack_path(
    source_asset: dict[str, Any],
    target_asset: dict[str, Any],
    chain_hops: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a multi-step attack path from sanitized graph-hop data."""
    hops = chain_hops or []
    exploitability = min(
        10.0,
        float(source_asset.get("exploitability_score") or 0.0)
        + float(target_asset.get("exposure_score") or 0.0)
        + sum(float(hop.get("weight") or 0.0) for hop in hops),
    )
    severity = _severity_for_score(exploitability)
    return {
        "source_asset": {"id": source_asset.get("id"), "hostname": source_asset.get("hostname")},
        "target_asset": {"id": target_asset.get("id"), "hostname": target_asset.get("hostname")},
        "hops": hops,
        "exploitability_score": round(exploitability, 2),
        "severity": severity,
        "summary": f"{len(hops)}-hop path from {source_asset.get('hostname')} to {target_asset.get('hostname')}.",
    }


def correlate_attack_chain(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge attack chains into a ranked reasoning set."""
    correlated: list[dict[str, Any]] = []
    for path in paths:
        chain = dict(path)
        chain["amplification"] = round(
            float(chain.get("exploitability_score") or 0.0)
            + float(chain.get("privilege_gain_score") or 0.0)
            + float(chain.get("trust_violation_score") or 0.0),
            2,
        )
        chain["severity"] = _severity_for_score(chain["amplification"])
        correlated.append(chain)

    return sorted(
        correlated,
        key=lambda item: (SEVERITY_RANK.get(str(item.get("severity") or "low"), 0), float(item.get("amplification") or 0.0)),
        reverse=True,
    )


def prioritize_exploitable_paths(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank attack paths by exploitability and blast potential."""
    return sorted(
        paths,
        key=lambda item: (
            float(item.get("exploitability_score") or 0.0),
            float(item.get("blast_radius_score") or 0.0),
            SEVERITY_RANK.get(str(item.get("severity") or "low"), 0),
        ),
        reverse=True,
    )