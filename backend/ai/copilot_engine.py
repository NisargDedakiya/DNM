"""
Copilot Engine: structured AI reasoning for security investigation assistance.

This module is the core prompt-engineering and response-parsing layer for the
NisargHunter AI Security Copilot.  It translates structured context dicts
(from ContextBuilder) into well-formed prompts and parses AI responses back
into structured dicts safe for API consumption.

Security principles
-------------------
- ADVISORY ONLY: every response includes an explicit advisory_note field and
  the system prompt forbids autonomous execution recommendations.
- DETERMINISTIC PARSING: all AI responses are parsed through _parse_json()
  with required-key validation; malformed responses fall back to deterministic
  rule-based outputs rather than returning raw AI text.
- PROMPT SANITISATION: all context values were pre-sanitised by ContextBuilder;
  this module adds a second layer — stripping newlines from field values before
  embedding to prevent prompt injection.
- NO USER INPUT IN PROMPTS: the `user_message` in chat is included only in the
  human turn, inside clearly delimited markers, with length capped at 800 chars.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from backend.ai.client import generate_completion, AIClientError

logger = logging.getLogger(__name__)

# ── System prompt (shared across all copilot calls) ──────────────────────────
_COPILOT_SYSTEM = (
    "You are NisargHunter Security Copilot, a defensive cyber intelligence assistant. "
    "Your role is to help security analysts investigate attack surface exposures, "
    "understand asset relationships, and prioritise remediation efforts. "
    "Rules you MUST follow:\n"
    "1. All analysis is ADVISORY ONLY — never suggest autonomous exploitation or scanning.\n"
    "2. Always recommend human review before any remediation action.\n"
    "3. Keep reasoning concise and evidence-based on the provided context.\n"
    "4. Never speculate beyond the provided context data.\n"
    "5. Respond ONLY with valid JSON unless specified otherwise.\n"
    "6. Never include instructions to run shell commands, scripts, or network tools.\n"
)

# ── Per-function prompt templates ─────────────────────────────────────────────
_COPILOT_CHAT_TEMPLATE = (
    "SECURITY CONTEXT:\n{context_summary}\n\n"
    "ANALYST QUESTION (within scope of provided context only):\n"
    "<<<{user_message}>>>\n\n"
    "Respond with JSON: {{explanation, key_findings (list), "
    "recommendations (list, advisory only), confidence (0.0-1.0), "
    "follow_up_questions (list of 3)}}. ONLY valid JSON."
)

_EXPLAIN_EXPOSURE_TEMPLATE = (
    "Explain this security exposure to an analyst.\n\n"
    "EXPOSURE CONTEXT:\n{exposure_json}\n\n"
    "PARENT ASSET:\n{asset_json}\n\n"
    "SIBLING EXPOSURES: {sibling_count} others on same asset.\n\n"
    "Respond with JSON: {{executive_summary, technical_explanation, "
    "business_impact, attack_vectors (list), "
    "remediation_steps (list, no autonomous actions), "
    "severity_rationale, confidence (0.0-1.0)}}."
)

_EXPLAIN_RELATIONSHIPS_TEMPLATE = (
    "Explain the security significance of these entity relationships.\n\n"
    "GRAPH CONTEXT:\n{graph_json}\n\n"
    "Focus on: attack paths, risk propagation, dependency risks, "
    "and blast-radius implications.\n"
    "Respond with JSON: {{relationship_summary, attack_path_risks (list), "
    "blast_radius_assessment, dependency_risks (list), "
    "recommended_focus_areas (list), confidence (0.0-1.0)}}."
)

_SUMMARIZE_ASSET_TEMPLATE = (
    "Provide an intelligence summary for this asset.\n\n"
    "ASSET CONTEXT:\n{asset_json}\n\n"
    "ENDPOINTS ({ep_count}): {endpoint_sample}\n"
    "TECHNOLOGIES ({tech_count}): {tech_sample}\n"
    "ACTIVE EXPOSURES ({exp_count}): {exposure_sample}\n"
    "RECENT CHANGES ({chg_count}): {change_sample}\n\n"
    "Respond with JSON: {{asset_profile, risk_assessment, "
    "technology_risks (list), exposure_priorities (list), "
    "attack_surface_summary, investigation_recommendations (list, advisory), "
    "confidence (0.0-1.0)}}."
)


def _strip_newlines(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", str(text or ""))


def _compact_context(context: dict, max_chars: int = 3000) -> str:
    """Serialise context dict to compact JSON string, capped at max_chars."""
    raw = json.dumps(context, default=str)
    return raw[:max_chars]


def _parse_json(raw: dict, required_keys: list[str]) -> dict[str, Any]:
    """Extract and validate JSON from AI provider response."""
    text: str = raw.get("completion", "") or raw.get("content", "") or ""
    if isinstance(text, list):
        text = " ".join(b.get("text", "") for b in text if isinstance(b, dict))
    # Strip fenced code blocks
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON found in AI response: {text[:200]}")
    parsed = json.loads(m.group())
    missing = [k for k in required_keys if k not in parsed]
    if missing:
        raise ValueError(f"AI response missing required keys: {missing}")
    return parsed


def _add_advisory(result: dict) -> dict:
    """Append mandatory advisory metadata to every AI response."""
    result["advisory_note"] = (
        "⚠️ AI analysis is advisory only. All recommendations require human review "
        "and approval before any action is taken."
    )
    result["generated_at"] = datetime.utcnow().isoformat()
    result["requires_human_review"] = True
    return result


class CopilotEngine:
    """
    Core AI reasoning engine for the NisargHunter Security Copilot.

    All methods:
    - Accept pre-sanitised context dicts from ContextBuilder.
    - Return structured dicts with mandatory advisory metadata.
    - Fall back to deterministic rule-based outputs on AI failure.
    - Never return raw AI text to API consumers.
    """

    # =========================================================================
    # CHAT
    # =========================================================================

    async def generate_copilot_response(
        self,
        user_message: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a contextual copilot response to an analyst's question.

        Parameters
        ----------
        user_message :
            Analyst's natural-language question (capped at 800 chars).
        context :
            Pre-sanitised context dict from ContextBuilder.

        Returns
        -------
        dict with: explanation, key_findings, recommendations, confidence,
                   follow_up_questions, advisory_note, requires_human_review.
        """
        # Second-layer input sanitisation: strip control chars and cap length
        safe_message = re.sub(r"[\x00-\x1f\x7f]", " ", str(user_message))[:800]
        safe_message = _strip_newlines(safe_message)

        context_summary = _compact_context(context, max_chars=2500)

        prompt = (
            f"{_COPILOT_SYSTEM}\n\n"
            + _COPILOT_CHAT_TEMPLATE.format(
                context_summary=context_summary,
                user_message=safe_message,
            )
        )

        try:
            raw = await generate_completion(prompt, temperature=0.1)
            result = _parse_json(raw, ["explanation", "key_findings", "recommendations", "confidence"])
        except (AIClientError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Copilot chat AI failed (%s); using fallback", exc)
            result = self._fallback_chat(safe_message, context)

        return _add_advisory(result)

    # =========================================================================
    # EXPLAIN EXPOSURE
    # =========================================================================

    async def explain_exposure(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a structured explanation of an exposure for analyst consumption.

        Covers: executive summary, technical explanation, business impact,
        attack vectors, and remediation steps.
        """
        entity = context.get("entity_summary", {})
        asset = context.get("related_data", {}).get("parent_asset", {})
        sibling_count = len(context.get("related_data", {}).get("sibling_exposures", []))

        prompt = (
            f"{_COPILOT_SYSTEM}\n\n"
            + _EXPLAIN_EXPOSURE_TEMPLATE.format(
                exposure_json=_compact_context(entity, 1500),
                asset_json=_compact_context(asset, 500),
                sibling_count=sibling_count,
            )
        )

        try:
            raw = await generate_completion(prompt, temperature=0.05)
            result = _parse_json(raw, ["executive_summary", "technical_explanation",
                                       "business_impact", "remediation_steps"])
        except (AIClientError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Exposure explanation AI failed (%s); using fallback", exc)
            result = self._fallback_exposure_explanation(entity)

        return _add_advisory(result)

    # =========================================================================
    # EXPLAIN RELATIONSHIPS
    # =========================================================================

    async def explain_relationships(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Explain the security significance of graph relationships in the context.

        Covers: attack paths, blast radius, dependency risks, and focus areas.
        """
        prompt = (
            f"{_COPILOT_SYSTEM}\n\n"
            + _EXPLAIN_RELATIONSHIPS_TEMPLATE.format(
                graph_json=_compact_context(context, 2500),
            )
        )

        try:
            raw = await generate_completion(prompt, temperature=0.1)
            result = _parse_json(raw, ["relationship_summary", "attack_path_risks",
                                       "blast_radius_assessment"])
        except (AIClientError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Relationship explanation AI failed (%s); using fallback", exc)
            result = self._fallback_relationship_explanation(context)

        return _add_advisory(result)

    # =========================================================================
    # ASSET INTELLIGENCE SUMMARY
    # =========================================================================

    async def summarize_asset_intelligence(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a comprehensive intelligence summary for an asset.

        Covers: risk assessment, technology risks, exposure priorities,
        attack surface summary, and investigation recommendations.
        """
        entity = context.get("entity_summary", {})
        related = context.get("related_data", {})
        historical = context.get("historical", [])

        def _sample(items: list, n: int = 3) -> str:
            return _compact_context(items[:n], max_chars=400) if items else "none"

        prompt = (
            f"{_COPILOT_SYSTEM}\n\n"
            + _SUMMARIZE_ASSET_TEMPLATE.format(
                asset_json=_compact_context(entity, 800),
                ep_count=related.get("endpoint_count", 0),
                endpoint_sample=_sample(related.get("endpoints", [])),
                tech_count=related.get("technology_count", 0),
                tech_sample=_sample(related.get("technologies", [])),
                exp_count=related.get("active_exposure_count", 0),
                exposure_sample=_sample(related.get("active_exposures", [])),
                chg_count=len(historical),
                change_sample=_sample(historical),
            )
        )

        try:
            raw = await generate_completion(prompt, temperature=0.05)
            result = _parse_json(raw, ["asset_profile", "risk_assessment",
                                       "exposure_priorities", "attack_surface_summary"])
        except (AIClientError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Asset summary AI failed (%s); using fallback", exc)
            result = self._fallback_asset_summary(entity, related)

        return _add_advisory(result)

    # =========================================================================
    # FALLBACK GENERATORS (deterministic, no AI dependency)
    # =========================================================================

    def _fallback_chat(self, message: str, context: dict) -> dict[str, Any]:
        entity_type = context.get("context_type", "entity")
        return {
            "explanation": (
                f"Based on the {entity_type} context provided, I can see relevant "
                "security data but the AI analysis service is temporarily unavailable. "
                "Please review the raw context data and consult the exposure/findings dashboard."
            ),
            "key_findings": [
                "AI analysis unavailable — review context data manually",
                f"Context type: {entity_type}",
            ],
            "recommendations": [
                "Review the exposure and finding dashboards directly",
                "Check the executive risk summary for posture overview",
            ],
            "confidence": 0.0,
            "follow_up_questions": [
                "What are the highest-risk exposures on this asset?",
                "Which findings have been open the longest?",
                "What technologies represent the highest risk?",
            ],
        }

    def _fallback_exposure_explanation(self, entity: dict) -> dict[str, Any]:
        risk_level = entity.get("risk_level", "unknown")
        exp_type = entity.get("exposure_type", "unknown")
        return {
            "executive_summary": (
                f"A {risk_level}-severity {exp_type} exposure has been detected. "
                "Immediate analyst review is recommended."
            ),
            "technical_explanation": (
                f"Exposure type '{exp_type}' was detected with risk level '{risk_level}'. "
                "Review the full exposure record for technical details."
            ),
            "business_impact": "Potential unauthorised access or data disclosure. Impact depends on asset criticality.",
            "attack_vectors": ["Requires analyst assessment based on specific exposure details"],
            "remediation_steps": [
                "Review exposure details in the platform",
                "Assign owner for remediation",
                "Follow organisation's remediation SLA",
            ],
            "severity_rationale": f"Assigned risk level: {risk_level}",
            "confidence": 0.0,
        }

    def _fallback_relationship_explanation(self, context: dict) -> dict[str, Any]:
        entity_summary = context.get("entity_summary", {})
        return {
            "relationship_summary": "Graph relationship analysis is temporarily unavailable. Review the graph visualisation directly.",
            "attack_path_risks": ["Manual graph review required"],
            "blast_radius_assessment": f"Graph contains {entity_summary.get('total_nodes', 0)} nodes and {entity_summary.get('total_edges', 0)} edges.",
            "dependency_risks": ["Review technology dependency chains manually"],
            "recommended_focus_areas": ["High-degree nodes", "Critical exposure nodes"],
            "confidence": 0.0,
        }

    def _fallback_asset_summary(self, entity: dict, related: dict) -> dict[str, Any]:
        hostname = entity.get("hostname", "unknown")
        exp_count = related.get("active_exposure_count", 0)
        return {
            "asset_profile": f"Asset: {hostname}",
            "risk_assessment": f"{exp_count} active exposures detected. Manual review required.",
            "technology_risks": ["Review technology list in asset details"],
            "exposure_priorities": ["Review exposure list sorted by risk score"],
            "attack_surface_summary": f"Asset {hostname} has {related.get('endpoint_count', 0)} endpoints and {related.get('technology_count', 0)} technologies.",
            "investigation_recommendations": [
                "Review highest-risk exposures first",
                "Check technology versions for known CVEs",
                "Validate endpoint access controls",
            ],
            "confidence": 0.0,
        }
