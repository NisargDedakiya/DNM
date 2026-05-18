"""
AI triage engine using Claude with deterministic structured outputs.

All responses are advisory-only and must be human-verified.
"""
from __future__ import annotations

from typing import Any

from backend.ai.claude_client import ClaudeClientError, generate_structured_response

_ALLOWED_PRIORITIES = {"P1", "P2", "P3", "P4", "P5"}


def _clamp01(value: Any) -> float:
    try:
        x = float(value)
    except Exception:
        return 0.0
    return min(max(x, 0.0), 1.0)


def _fallback_priority(exploitability_score: float, confidence_score: float) -> str:
    combined = (exploitability_score * 0.65) + (confidence_score * 0.35)
    if combined >= 0.88:
        return "P1"
    if combined >= 0.72:
        return "P2"
    if combined >= 0.55:
        return "P3"
    if combined >= 0.35:
        return "P4"
    return "P5"


async def classify_finding(context: dict[str, Any], organization_id: str | None = None) -> dict[str, Any]:
    """Classify finding into P1-P5 with structured reasoning."""
    prompt = (
        "Classify this security finding using priority classes P1-P5. "
        "Focus on exploitability, internet exposure, auth impact, and business impact. "
        "Return conservative assessment and avoid overstatement.\n\n"
        f"Finding title: {context.get('title')}\n"
        f"Scanner severity: {context.get('scanner_severity')}\n"
        f"Endpoint: {context.get('endpoint')}\n"
        f"Exploitability score: {context.get('exploitability_score')}\n"
        f"Confidence score: {context.get('confidence_score')}\n"
        f"Signals: {context.get('signals')}\n"
    )

    try:
        result = await generate_structured_response(
            prompt,
            organization_id=organization_id,
            required_keys=["priority", "rationale", "recommended_severity"],
        )
        data = result["data"]
        priority = str(data.get("priority", "")).upper()
        if priority not in _ALLOWED_PRIORITIES:
            priority = _fallback_priority(
                _clamp01(context.get("exploitability_score")),
                _clamp01(context.get("confidence_score")),
            )

        return {
            "priority": priority,
            "rationale": str(data.get("rationale", "")).strip()[:3000],
            "recommended_severity": str(data.get("recommended_severity", "high")).lower(),
            "source": "ai",
        }
    except Exception:
        return {
            "priority": _fallback_priority(
                _clamp01(context.get("exploitability_score")),
                _clamp01(context.get("confidence_score")),
            ),
            "rationale": "Fallback classification used due to AI parsing/availability issue.",
            "recommended_severity": str(context.get("scanner_severity", "medium")).lower(),
            "source": "fallback",
        }


async def analyze_exploitability(context: dict[str, Any], organization_id: str | None = None) -> dict[str, Any]:
    """Request AI exploitability reasoning with structured output."""
    prompt = (
        "Analyze exploitability for this finding in a defensive triage context. "
        "Do not provide exploit steps. Return only risk-oriented reasoning.\n\n"
        f"Title: {context.get('title')}\n"
        f"Endpoint: {context.get('endpoint')}\n"
        f"Auth involvement: {context.get('auth_involvement')}\n"
        f"Exposure context: {context.get('exposure_context')}\n"
        f"Graph context: {context.get('graph_context')}\n"
    )

    try:
        result = await generate_structured_response(
            prompt,
            organization_id=organization_id,
            required_keys=["exploitability_score", "reasoning", "key_indicators"],
        )
        data = result["data"]
        return {
            "exploitability_score": _clamp01(data.get("exploitability_score")),
            "reasoning": str(data.get("reasoning", "")).strip()[:3000],
            "key_indicators": data.get("key_indicators", []),
            "source": "ai",
        }
    except Exception:
        return {
            "exploitability_score": _clamp01(context.get("exploitability_score")),
            "reasoning": "Fallback exploitability analysis used due to AI parsing/availability issue.",
            "key_indicators": [],
            "source": "fallback",
        }


async def generate_confidence_score(context: dict[str, Any], organization_id: str | None = None) -> dict[str, Any]:
    """Generate confidence reasoning from context and deterministic signals."""
    prompt = (
        "Analyze confidence score for this finding and explain uncertainty factors. "
        "Return conservative confidence to reduce false positives.\n\n"
        f"Title: {context.get('title')}\n"
        f"Evidence quality: {context.get('evidence_quality')}\n"
        f"Duplicate count: {context.get('duplicate_count')}\n"
        f"Signal factors: {context.get('signals')}\n"
    )

    try:
        result = await generate_structured_response(
            prompt,
            organization_id=organization_id,
            required_keys=["confidence_score", "confidence_reasoning", "uncertainty_factors"],
        )
        data = result["data"]
        return {
            "confidence_score": _clamp01(data.get("confidence_score")),
            "confidence_reasoning": str(data.get("confidence_reasoning", "")).strip()[:3000],
            "uncertainty_factors": data.get("uncertainty_factors", []),
            "source": "ai",
        }
    except Exception:
        return {
            "confidence_score": _clamp01(context.get("confidence_score")),
            "confidence_reasoning": "Fallback confidence reasoning used due to AI parsing/availability issue.",
            "uncertainty_factors": [],
            "source": "fallback",
        }


async def summarize_risk(context: dict[str, Any], organization_id: str | None = None) -> dict[str, Any]:
    """Produce executive triage summary and verification guidance."""
    prompt = (
        "Create a short advisory-only triage summary. "
        "Include why this matters and what human verification should check next.\n\n"
        f"Priority: {context.get('priority')}\n"
        f"Exploitability: {context.get('exploitability_score')}\n"
        f"Confidence: {context.get('confidence_score')}\n"
        f"Endpoint: {context.get('endpoint')}\n"
    )

    try:
        result = await generate_structured_response(
            prompt,
            organization_id=organization_id,
            required_keys=["summary", "verification_steps", "risk_statement"],
        )
        data = result["data"]
        return {
            "summary": str(data.get("summary", "")).strip()[:3000],
            "verification_steps": data.get("verification_steps", []),
            "risk_statement": str(data.get("risk_statement", "")).strip()[:3000],
            "source": "ai",
        }
    except Exception:
        return {
            "summary": "Fallback summary: human verification required before confirming this finding.",
            "verification_steps": [
                "Validate scope and endpoint ownership",
                "Reproduce evidence in a controlled, non-destructive manner",
                "Confirm business impact assumptions",
            ],
            "risk_statement": "Potentially actionable security signal pending analyst validation.",
            "source": "fallback",
        }
