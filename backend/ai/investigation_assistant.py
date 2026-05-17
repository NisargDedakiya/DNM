"""
Investigation Assistant: guided investigation workflows and step recommendations.

This module sits above CopilotEngine and ContextBuilder to provide
end-to-end guided investigation workflows.  It orchestrates context
assembly, AI explanation, and recommendation generation for the three
primary investigation targets: assets, exposures, and full investigations.

Advisory contract
-----------------
- investigate_asset() / investigate_exposure() always include
  ``requires_human_review: True`` and ``advisory_note`` in their output.
- recommend_investigation_steps() returns ordered investigation actions
  that require explicit analyst confirmation — never autonomous execution.
- generate_investigation_summary() synthesises findings into a narrative
  that clearly labels all AI-generated content as advisory.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.context_builder import ContextBuilder
from backend.ai.copilot_engine import CopilotEngine
from backend.ai.client import generate_completion, AIClientError

logger = logging.getLogger(__name__)

_INVESTIGATION_STEPS_TEMPLATE = (
    "Given this security investigation context, recommend an ordered set of "
    "investigation steps for a security analyst.\n\n"
    "CONTEXT TYPE: {context_type}\n"
    "ENTITY SUMMARY: {entity_summary}\n"
    "RISK LEVEL: {risk_level}\n"
    "ACTIVE EXPOSURES: {exposure_count}\n"
    "GRAPH CONNECTIONS: {graph_connections}\n\n"
    "Rules:\n"
    "- All steps are for HUMAN analysts only — no autonomous actions.\n"
    "- Each step requires explicit analyst approval before execution.\n"
    "- Steps must be scoped to authorised assessment boundaries.\n\n"
    "Respond with JSON: {{investigation_plan (list of {{step_number, action, "
    "rationale, expected_output, requires_human_approval: true}}), "
    "priority_focus, estimated_effort, confidence (0.0-1.0)}}."
)

_INVESTIGATION_SUMMARY_TEMPLATE = (
    "Generate an investigation summary report for a security analyst.\n\n"
    "INVESTIGATION CONTEXT:\n{context_json}\n\n"
    "AI FINDINGS SO FAR:\n{findings_json}\n\n"
    "Provide a concise, evidence-based investigation summary.\n"
    "Respond with JSON: {{investigation_title, executive_summary, "
    "key_findings (list), risk_verdict, recommended_next_actions (list, advisory), "
    "open_questions (list), confidence (0.0-1.0)}}."
)


def _s(v: Any, n: int = 200) -> str:
    return re.sub(r"[\x00-\x1f\x7f`\"\\]", " ", str(v or ""))[:n].strip()


def _compact(obj: Any, n: int = 1500) -> str:
    return json.dumps(obj, default=str)[:n]


class InvestigationAssistant:
    """
    Guided investigation workflow engine.

    Orchestrates ContextBuilder + CopilotEngine to produce end-to-end
    investigation packages for assets, exposures, and custom investigations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._ctx = ContextBuilder(db)
        self._engine = CopilotEngine()

    # =========================================================================
    # INVESTIGATE ASSET
    # =========================================================================

    async def investigate_asset(
        self,
        organization_id: UUID,
        asset_id: UUID,
    ) -> dict[str, Any]:
        """
        Full AI-assisted investigation package for an asset.

        Assembles context → explains intelligence → recommends steps.

        Returns
        -------
        dict with:
            context         – raw asset context
            ai_summary      – AI intelligence summary (advisory)
            investigation_steps – ordered analyst checklist (advisory)
            advisory_note   – mandatory advisory disclaimer
        """
        context = await self._ctx.build_asset_context(organization_id, asset_id)

        if "error" in context:
            return {
                "error": context["error"],
                "advisory_note": "Investigation aborted — entity not found.",
                "requires_human_review": True,
            }

        # AI intelligence summary
        ai_summary = await self._engine.summarize_asset_intelligence(context)

        # Investigation step recommendations
        steps = await self.recommend_investigation_steps(
            context_type="asset",
            entity_summary=context.get("entity_summary", {}),
            risk_level=context["entity_summary"].get("risk_score", 0),
            exposure_count=context["related_data"].get("active_exposure_count", 0),
            graph_connections=context.get("graph_hints", {}).get("total_connections", 0),
        )

        return {
            "investigation_type": "asset",
            "entity_id": str(asset_id),
            "organization_id": str(organization_id),
            "context": context,
            "ai_summary": ai_summary,
            "investigation_steps": steps,
            "advisory_note": (
                "⚠️ All AI analysis is advisory only. "
                "No action should be taken without explicit human analyst review and approval."
            ),
            "requires_human_review": True,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # INVESTIGATE EXPOSURE
    # =========================================================================

    async def investigate_exposure(
        self,
        organization_id: UUID,
        exposure_id: UUID,
    ) -> dict[str, Any]:
        """
        Full AI-assisted investigation package for an exposure.

        Assembles context → explains exposure → recommends investigation steps.

        Returns
        -------
        dict with:
            context         – raw exposure context
            ai_explanation  – structured exposure explanation (advisory)
            investigation_steps – ordered analyst checklist (advisory)
            advisory_note   – mandatory advisory disclaimer
        """
        context = await self._ctx.build_exposure_context(organization_id, exposure_id)

        if "error" in context:
            return {
                "error": context["error"],
                "advisory_note": "Investigation aborted — entity not found.",
                "requires_human_review": True,
            }

        # AI exposure explanation
        ai_explanation = await self._engine.explain_exposure(context)

        # Investigation steps
        entity = context.get("entity_summary", {})
        steps = await self.recommend_investigation_steps(
            context_type="exposure",
            entity_summary=entity,
            risk_level=entity.get("risk_level", "unknown"),
            exposure_count=len(context.get("related_data", {}).get("sibling_exposures", [])) + 1,
            graph_connections=context.get("graph_hints", {}).get("total_connections", 0),
        )

        return {
            "investigation_type": "exposure",
            "entity_id": str(exposure_id),
            "organization_id": str(organization_id),
            "context": context,
            "ai_explanation": ai_explanation,
            "investigation_steps": steps,
            "advisory_note": (
                "⚠️ All AI analysis is advisory only. "
                "Remediation steps require human analyst review and approval before execution."
            ),
            "requires_human_review": True,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # RECOMMEND INVESTIGATION STEPS
    # =========================================================================

    async def recommend_investigation_steps(
        self,
        context_type: str,
        entity_summary: dict[str, Any],
        risk_level: Any,
        exposure_count: int,
        graph_connections: int,
    ) -> dict[str, Any]:
        """
        Generate an ordered investigation checklist for an analyst.

        All steps include ``requires_human_approval: true`` and are scoped
        to authorised assessment boundaries.

        Returns
        -------
        dict with: investigation_plan, priority_focus, estimated_effort, confidence.
        """
        prompt = (
            f"You are a defensive security investigation advisor. "
            f"Advisory only — no autonomous actions.\n\n"
            + _INVESTIGATION_STEPS_TEMPLATE.format(
                context_type=_s(context_type),
                entity_summary=_compact(entity_summary, 800),
                risk_level=_s(risk_level),
                exposure_count=exposure_count,
                graph_connections=graph_connections,
            )
        )

        try:
            raw = await generate_completion(prompt, temperature=0.1)
            result = _parse_json_local(raw, ["investigation_plan", "priority_focus"])
        except (AIClientError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Investigation steps AI failed (%s); using fallback", exc)
            result = self._fallback_steps(context_type, exposure_count)

        result["advisory_note"] = (
            "All investigation steps are advisory. Each step requires explicit human analyst approval."
        )
        result["requires_human_review"] = True
        result["generated_at"] = datetime.utcnow().isoformat()
        return result

    # =========================================================================
    # GENERATE INVESTIGATION SUMMARY
    # =========================================================================

    async def generate_investigation_summary(
        self,
        context: dict[str, Any],
        findings_so_far: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Synthesise a complete investigation summary from context and AI findings.

        Designed to be called after investigate_asset() or investigate_exposure()
        to produce a final, shareable investigation report payload.

        Returns
        -------
        dict with: investigation_title, executive_summary, key_findings,
                   risk_verdict, recommended_next_actions, open_questions,
                   confidence, advisory_note.
        """
        prompt = (
            "You are a defensive security investigation advisor. Advisory only.\n\n"
            + _INVESTIGATION_SUMMARY_TEMPLATE.format(
                context_json=_compact(context, 1500),
                findings_json=_compact(findings_so_far or {}, 800),
            )
        )

        try:
            raw = await generate_completion(prompt, temperature=0.05)
            result = _parse_json_local(raw, ["investigation_title", "executive_summary",
                                             "key_findings", "risk_verdict"])
        except (AIClientError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Investigation summary AI failed (%s); using fallback", exc)
            result = self._fallback_summary(context)

        result["advisory_note"] = (
            "⚠️ This investigation summary is AI-generated and advisory only. "
            "Human analyst review is required before any action."
        )
        result["requires_human_review"] = True
        result["generated_at"] = datetime.utcnow().isoformat()
        return result

    # =========================================================================
    # FALLBACKS
    # =========================================================================

    def _fallback_steps(self, context_type: str, exposure_count: int) -> dict[str, Any]:
        base_steps = [
            {
                "step_number": 1,
                "action": f"Review {context_type} details in the platform dashboard",
                "rationale": "Establish baseline understanding before deeper investigation",
                "expected_output": "Full entity detail view",
                "requires_human_approval": True,
            },
            {
                "step_number": 2,
                "action": f"Review {exposure_count} active exposure(s) sorted by risk score",
                "rationale": "Highest-risk exposures need prioritised attention",
                "expected_output": "Prioritised exposure list",
                "requires_human_approval": True,
            },
            {
                "step_number": 3,
                "action": "Check graph relationships for blast-radius implications",
                "rationale": "Understand which other entities are connected and at risk",
                "expected_output": "Graph neighbourhood view",
                "requires_human_approval": True,
            },
            {
                "step_number": 4,
                "action": "Review historical timeline for recent changes",
                "rationale": "Identify when risk changed and what triggered it",
                "expected_output": "Timeline of change events",
                "requires_human_approval": True,
            },
            {
                "step_number": 5,
                "action": "Document investigation findings and assign remediation owners",
                "rationale": "Ensure accountability for remediation",
                "expected_output": "Assigned remediation tasks",
                "requires_human_approval": True,
            },
        ]
        return {
            "investigation_plan": base_steps,
            "priority_focus": "Begin with highest-risk exposures",
            "estimated_effort": "2-4 hours for a thorough investigation",
            "confidence": 0.0,
        }

    def _fallback_summary(self, context: dict) -> dict[str, Any]:
        entity = context.get("entity_summary", {})
        ctx_type = context.get("context_type", "entity")
        return {
            "investigation_title": f"Security Investigation: {ctx_type.title()} {context.get('entity_id', '')[:8]}",
            "executive_summary": "AI summary generation is temporarily unavailable. Review the context data directly.",
            "key_findings": [
                "AI analysis temporarily unavailable",
                f"Manual review of {ctx_type} data is recommended",
            ],
            "risk_verdict": "Unknown — requires manual analyst assessment",
            "recommended_next_actions": [
                "Review exposure dashboard",
                "Check executive security posture report",
            ],
            "open_questions": [
                "What is the full scope of exposure on this entity?",
                "Are there related entities that share this risk?",
            ],
            "confidence": 0.0,
        }


def _parse_json_local(raw: dict, required_keys: list[str]) -> dict[str, Any]:
    """Local JSON parser (mirrors CopilotEngine pattern)."""
    text: str = raw.get("completion", "") or raw.get("content", "") or ""
    if isinstance(text, list):
        text = " ".join(b.get("text", "") for b in text if isinstance(b, dict))
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON in AI response: {text[:200]}")
    parsed = json.loads(m.group())
    missing = [k for k in required_keys if k not in parsed]
    if missing:
        raise ValueError(f"Missing keys: {missing}")
    return parsed
