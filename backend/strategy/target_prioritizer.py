"""
Target prioritization helpers for org-scoped hunt planning.
"""
from __future__ import annotations

from typing import Any


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def calculate_target_value(target: dict[str, Any]) -> float:
    """Calculate an exploitability-aware business value score."""
    business = _as_float(target.get("business_criticality"), 0.0)
    risk = _as_float(target.get("risk_score"), 0.0)
    exposure = _as_float(target.get("exposure_score"), 0.0)
    threat = _as_float(target.get("threat_score"), 0.0)
    auth = 1.2 if target.get("has_auth") else 0.9
    graphql = 1.15 if target.get("has_graphql") else 1.0
    internet = 1.25 if target.get("internet_facing") else 0.95
    return round((business * 2.2 + risk * 2.0 + exposure * 1.8 + threat * 1.6) * auth * graphql * internet, 2)


def identify_high_signal_assets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Highlight assets with auth, API, GraphQL, and admin signals."""
    signal_keywords = {"auth", "oauth", "graphql", "admin", "api", "dashboard", "panel", "gateway"}
    scored = []
    for target in targets:
        name = str(target.get("name") or target.get("hostname") or target.get("asset") or "unknown")
        tags = {str(tag).lower() for tag in target.get("tags", [])}
        score = sum(1 for keyword in signal_keywords if keyword in name.lower() or keyword in tags)
        if target.get("internet_facing"):
            score += 2
        if target.get("has_auth"):
            score += 2
        if target.get("has_graphql"):
            score += 2
        scored.append({**target, "signal_score": score})
    return sorted(scored, key=lambda item: item.get("signal_score", 0), reverse=True)


def prioritize_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank targets by criticality and exploitability signals."""
    ranked = []
    for target in identify_high_signal_assets(targets):
        ranked.append({
            **target,
            "priority_score": calculate_target_value(target),
            "priority_reason": target.get("priority_reason") or "Business-critical exposure with attack-path relevance.",
        })
    return sorted(ranked, key=lambda item: item["priority_score"], reverse=True)
