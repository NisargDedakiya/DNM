"""
Adaptive recon helpers for evolving hunt recommendations.
"""
from __future__ import annotations

from typing import Any


def prioritize_followup_scans(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Prioritize follow-up scans based on recent findings and exposures."""
    findings = int(context.get("critical_findings", 0))
    exposures = int(context.get("active_exposures", 0))
    followups = [
        {"scan_type": "auth_review", "priority": 90 + findings, "reason": "Auth systems and session boundaries are high-signal."},
        {"scan_type": "graphql_surface", "priority": 80 + exposures, "reason": "GraphQL and schema discovery often reveal broader reach."},
        {"scan_type": "admin_portal", "priority": 75 + findings, "reason": "Admin panels and trust boundaries need revalidation."},
        {"scan_type": "cloud_dashboard", "priority": 70 + exposures, "reason": "Cloud dashboards and public management APIs can expand blast radius."},
    ]
    return sorted(followups, key=lambda item: item["priority"], reverse=True)


def evolve_scan_strategy(context: dict[str, Any]) -> dict[str, Any]:
    """Evolve scan strategy using current intelligence signals."""
    return {
        "scan_focus": context.get("scan_focus") or ["auth", "graphql", "admin", "cloud"],
        "follow_up_scans": prioritize_followup_scans(context),
        "evolution_reason": context.get("evolution_reason") or "Adjusted using new attack-path, exposure, and monitoring signals.",
        "requires_human_approval": True,
    }


def adapt_recon_flow(context: dict[str, Any]) -> dict[str, Any]:
    """Adapt recon flow for the current campaign state."""
    evolved = evolve_scan_strategy(context)
    return {
        "organization_id": context.get("organization_id"),
        "campaign_name": context.get("campaign_name") or "advisory-campaign",
        "strategy": evolved,
        "next_actions": [
            "validate_scope_boundary",
            "prioritize_high_signal_targets",
            "stage_recommendations_for_approval",
            "correlate_new_findings",
        ],
        "advisory_note": "Adaptive recon remains approval-gated and workspace-isolated.",
    }
