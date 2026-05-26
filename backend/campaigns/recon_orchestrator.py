"""
Recon orchestration helpers for approved campaign sequencing.
"""
from __future__ import annotations

from typing import Any


def optimize_scan_sequence(campaign: dict[str, Any], signals: dict[str, Any]) -> list[dict[str, Any]]:
    """Sequence approved scan phases by risk and signal density."""
    phases = campaign.get("methodology", {}).get("playbook", {}).get("sequence", [])
    prioritized = []
    for phase in phases:
        prioritized.append({
            **phase,
            "estimated_priority": 100 - (phase.get("step", 1) * 10) + len(signals.get("high_signal_assets", [])),
        })
    return sorted(prioritized, key=lambda item: item["estimated_priority"], reverse=True)


def correlate_recon_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge recon signals into a safe campaign summary."""
    summary = {
        "total_results": len(results),
        "critical_signals": 0,
        "auth_signals": 0,
        "graphql_signals": 0,
        "admin_signals": 0,
    }
    for item in results:
        severity = str(item.get("severity") or "").lower()
        target = str(item.get("target") or item.get("hostname") or "").lower()
        if severity in {"critical", "high"}:
            summary["critical_signals"] += 1
        if any(token in target for token in ["auth", "login", "sso", "oauth"]):
            summary["auth_signals"] += 1
        if "graphql" in target:
            summary["graphql_signals"] += 1
        if any(token in target for token in ["admin", "dashboard", "panel"]):
            summary["admin_signals"] += 1
    return summary


def orchestrate_recon(campaign: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    """Orchestrate a safe, approved recon campaign summary."""
    sequence = optimize_scan_sequence(campaign, {"high_signal_assets": campaign.get("prioritized_targets", [])})
    correlation = correlate_recon_results(results)
    return {
        "campaign_name": campaign.get("campaign_name"),
        "status": campaign.get("status", "pending_approval"),
        "sequence": sequence,
        "correlation": correlation,
        "requires_human_approval": True,
    }
