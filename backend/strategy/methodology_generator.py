"""
Methodology generation helpers for advisory hunt planning.
"""
from __future__ import annotations

from typing import Any


def adapt_strategy_context(context: dict[str, Any]) -> dict[str, Any]:
    """Normalize context into a safe planning shape."""
    focus = [str(item).lower() for item in context.get("focus_areas", []) if item]
    if not focus:
        focus = ["auth", "graphql", "admin", "cloud"]
    return {
        "focus_areas": focus[:6],
        "internet_facing": bool(context.get("internet_facing", True)),
        "approval_required": True,
        "scope_notes": context.get("scope_notes") or "Stay within approved workspace boundaries.",
        "risk_signals": context.get("risk_signals", []),
        "monitoring_signals": context.get("monitoring_signals", []),
    }


def create_recon_playbook(context: dict[str, Any]) -> dict[str, Any]:
    """Create an approved recon playbook with sequencing and guardrails."""
    adapted = adapt_strategy_context(context)
    focus = adapted["focus_areas"]
    sequence = []
    for index, phase in enumerate([
        ("scope validation", "Confirm workspace scope, approval gates, and safe execution boundaries."),
        ("target enrichment", "Correlate threats, exposures, and attack-path signals."),
        ("high-signal probing", "Prioritize auth systems, GraphQL, admin panels, and internet-facing APIs."),
        ("follow-up adaptation", "Refine the plan using new findings and monitoring alerts."),
    ], start=1):
        sequence.append({
            "step": index,
            "phase": phase[0],
            "rationale": phase[1],
            "focus": focus[min(index - 1, len(focus) - 1)],
        })
    return {
        "playbook_name": "Advisory Recon Playbook",
        "objective": "Prioritize safe, approved recon paths against the highest-signal assets.",
        "focus_areas": focus,
        "sequence": sequence,
        "approval_required": True,
        "guardrails": [
            "No scope expansion",
            "No autonomous execution",
            "No cross-org intelligence sharing",
            "Audit every recommendation",
        ],
    }


def generate_methodology(context: dict[str, Any]) -> dict[str, Any]:
    """Generate a contextual methodology for an approved hunt."""
    playbook = create_recon_playbook(context)
    return {
        "methodology_name": f"{playbook['playbook_name']} - {context.get('strategy_type', 'hunt')}",
        "playbook": playbook,
        "strategy_context": adapt_strategy_context(context),
        "recommended_stages": [
            "scope review",
            "asset and exposure correlation",
            "target prioritization",
            "campaign staging",
            "adaptive follow-up",
        ],
        "confidence": round(0.72 + min(len(playbook["focus_areas"]), 4) * 0.05, 2),
    }
