"""
AI-assisted hunt planning helpers.
"""
from __future__ import annotations

from typing import Any

from backend.strategy.methodology_generator import generate_methodology, adapt_strategy_context
from backend.strategy.target_prioritizer import prioritize_targets


def prioritize_recon_sequence(targets: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    """Order recon targets by priority and safe signal density."""
    ranked = prioritize_targets(targets)
    for index, target in enumerate(ranked, start=1):
        target["sequence_order"] = index
    if context.get("monitoring_signals"):
        ranked.sort(key=lambda item: (item.get("priority_score", 0), item.get("signal_score", 0)), reverse=True)
    return ranked


def adapt_hunt_strategy(current_plan: dict[str, Any], new_signals: dict[str, Any]) -> dict[str, Any]:
    """Adapt a hunt plan based on new org-scoped intel."""
    updated = dict(current_plan)
    adapted_context = adapt_strategy_context({
        "focus_areas": new_signals.get("focus_areas") or current_plan.get("focus_areas", []),
        "monitoring_signals": new_signals.get("monitoring_signals", []),
        "risk_signals": new_signals.get("risk_signals", []),
        "scope_notes": new_signals.get("scope_notes") or current_plan.get("scope_notes"),
    })
    updated["focus_areas"] = adapted_context["focus_areas"]
    updated["approval_required"] = True
    updated["adaptive_notes"] = new_signals.get("notes") or "Adjusted using the latest monitoring and exposure signals."
    updated["methodology"] = generate_methodology({
        "strategy_type": current_plan.get("strategy_type", "hunt"),
        **adapted_context,
    })
    return updated


def generate_hunt_plan(organization_id: str, targets: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    """Generate an advisory hunt plan for an organization."""
    adapted = adapt_strategy_context(context)
    prioritized_targets = prioritize_recon_sequence(targets, adapted)
    methodology = generate_methodology({
        "strategy_type": context.get("strategy_type", "hunt"),
        **adapted,
    })
    return {
        "organization_id": organization_id,
        "strategy_type": context.get("strategy_type", "hunt"),
        "target_scope": [target.get("name") or target.get("hostname") or target.get("asset") for target in prioritized_targets],
        "priority_score": round(sum(item.get("priority_score", 0.0) for item in prioritized_targets[:5]) / max(len(prioritized_targets[:5]), 1), 2),
        "focus_areas": adapted["focus_areas"],
        "prioritized_targets": prioritized_targets,
        "methodology": methodology,
        "approval_required": True,
        "advisory_note": "All hunt actions require human approval and workspace scope validation.",
    }
