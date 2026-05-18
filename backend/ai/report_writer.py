"""
AI-assisted report writer for structured bug bounty reports.

Security posture:
- advisory-only output
- factual grounding from provided context
- deterministic section layout
- human review required before external submission
"""
from __future__ import annotations

import re
from typing import Any

from backend.ai.claude_client import generate_structured_response

_HACKERONE_LEVELS = {"critical", "high", "medium", "low"}
_BUGCROWD_LEVELS = {"p1", "p2", "p3", "p4", "p5"}


def _sanitize_text(value: str | None, max_len: int = 6000) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    patterns = [
        r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+",
        r"(?i)authorization\s*[:=]\s*[^\s,;]+",
        r"(?i)cookie\s*[:=]\s*[^\s,;]+",
        r"AKIA[0-9A-Z]{16}",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text)
    return text[:max_len]


def _normalize_platform(platform: str | None) -> str:
    normalized = str(platform or "hackerone").strip().lower()
    if normalized not in {"hackerone", "bugcrowd"}:
        return "hackerone"
    return normalized


def _map_severity_to_platform(severity: str | None, platform: str) -> str:
    raw = str(severity or "medium").strip().lower()
    platform_name = _normalize_platform(platform)

    if platform_name == "hackerone":
        mapping = {
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "info": "Low",
            "p1": "Critical",
            "p2": "High",
            "p3": "Medium",
            "p4": "Low",
            "p5": "Low",
        }
        level = mapping.get(raw, "Medium")
        return level if level.lower() in _HACKERONE_LEVELS else "Medium"

    mapping = {
        "critical": "P1",
        "high": "P2",
        "medium": "P3",
        "low": "P4",
        "info": "P5",
        "p1": "P1",
        "p2": "P2",
        "p3": "P3",
        "p4": "P4",
        "p5": "P5",
    }
    level = mapping.get(raw, "P3")
    return level if level.lower() in _BUGCROWD_LEVELS else "P3"


def _fallback_reproduction_steps(context: dict[str, Any]) -> list[str]:
    endpoint = _sanitize_text(str(context.get("endpoint") or context.get("affected_asset") or ""), 800)
    evidence = _sanitize_text(str(context.get("evidence") or ""), 1000)
    steps = [
        "Open the affected asset in an authorized testing session.",
        "Navigate to the vulnerable endpoint and apply the exact request pattern observed during testing.",
        "Compare server behavior against expected secure behavior and capture deterministic response differences.",
    ]
    if endpoint:
        steps.insert(1, f"Target endpoint: {endpoint}")
    if evidence:
        steps.append(f"Reference observed evidence: {evidence[:400]}")
    return steps


async def generate_reproduction_steps(context: dict[str, Any], organization_id: str | None = None) -> dict[str, Any]:
    """Generate clear, reproducible, non-destructive reproduction guidance."""
    prompt = (
        "Generate concise, reproducible, and non-destructive vulnerability reproduction steps. "
        "Do not provide exploit automation or payload weaponization. "
        "Use only supplied evidence and clearly mark assumptions. "
        "Return JSON with keys: steps (array), prerequisites (array), validation_checks (array).\n\n"
        f"Title: {_sanitize_text(context.get('title'))}\n"
        f"Severity: {_sanitize_text(context.get('severity'))}\n"
        f"Affected Asset: {_sanitize_text(context.get('affected_asset') or context.get('endpoint'))}\n"
        f"Description: {_sanitize_text(context.get('description'))}\n"
        f"Evidence: {_sanitize_text(context.get('evidence'))}\n"
    )
    try:
        response = await generate_structured_response(
            prompt,
            organization_id=organization_id,
            required_keys=["steps", "prerequisites", "validation_checks"],
        )
        data = response["data"]
        steps = [str(step).strip() for step in data.get("steps", []) if str(step).strip()]
        if not steps:
            steps = _fallback_reproduction_steps(context)
        return {
            "steps": steps,
            "prerequisites": [str(item).strip() for item in data.get("prerequisites", []) if str(item).strip()],
            "validation_checks": [str(item).strip() for item in data.get("validation_checks", []) if str(item).strip()],
            "source": "ai",
        }
    except Exception:
        return {
            "steps": _fallback_reproduction_steps(context),
            "prerequisites": ["Authorized test account", "In-scope asset access"],
            "validation_checks": ["Observed behavior is repeatable", "Security impact aligns with evidence"],
            "source": "fallback",
        }


async def generate_business_impact(context: dict[str, Any], organization_id: str | None = None) -> dict[str, Any]:
    """Generate factual, evidence-grounded business impact narrative."""
    prompt = (
        "Write business impact for a security report using only proven observations. "
        "Avoid hypothetical exaggeration. "
        "Return JSON with keys: impact_summary, impacted_workflows (array), confidence_statement.\n\n"
        f"Title: {_sanitize_text(context.get('title'))}\n"
        f"Affected Asset: {_sanitize_text(context.get('affected_asset') or context.get('endpoint'))}\n"
        f"Severity: {_sanitize_text(context.get('severity'))}\n"
        f"Evidence: {_sanitize_text(context.get('evidence'))}\n"
        f"Triage Summary: {_sanitize_text(context.get('triage_summary'))}\n"
    )
    try:
        response = await generate_structured_response(
            prompt,
            organization_id=organization_id,
            required_keys=["impact_summary", "impacted_workflows", "confidence_statement"],
        )
        data = response["data"]
        return {
            "impact_summary": _sanitize_text(data.get("impact_summary"), 2000),
            "impacted_workflows": [
                _sanitize_text(str(item), 240) for item in data.get("impacted_workflows", []) if str(item).strip()
            ],
            "confidence_statement": _sanitize_text(data.get("confidence_statement"), 600),
            "source": "ai",
        }
    except Exception:
        severity = _sanitize_text(context.get("severity"), 64) or "Medium"
        return {
            "impact_summary": (
                "Observed behavior indicates a security control weakness with measurable risk to confidentiality, "
                "integrity, or availability depending on affected workflows."
            ),
            "impacted_workflows": ["User authentication", "Administrative operations", "API request handling"],
            "confidence_statement": f"Conservative impact estimate based on validated evidence and {severity} severity context.",
            "source": "fallback",
        }


async def generate_remediation(context: dict[str, Any], organization_id: str | None = None) -> dict[str, Any]:
    """Generate remediation content with defensive and verifiable guidance."""
    prompt = (
        "Generate remediation guidance for a bug bounty report. "
        "Provide defensive controls, validation checks, and implementation notes. "
        "Do not include exploit guidance. "
        "Return JSON with keys: remediation_summary, fix_steps (array), verification_plan (array).\n\n"
        f"Title: {_sanitize_text(context.get('title'))}\n"
        f"Vulnerability Type: {_sanitize_text(context.get('vulnerability_type'))}\n"
        f"Technology Stack: {_sanitize_text(context.get('technology_stack'))}\n"
        f"Evidence: {_sanitize_text(context.get('evidence'))}\n"
    )
    try:
        response = await generate_structured_response(
            prompt,
            organization_id=organization_id,
            required_keys=["remediation_summary", "fix_steps", "verification_plan"],
        )
        data = response["data"]
        return {
            "remediation_summary": _sanitize_text(data.get("remediation_summary"), 2000),
            "fix_steps": [
                _sanitize_text(str(item), 300) for item in data.get("fix_steps", []) if str(item).strip()
            ],
            "verification_plan": [
                _sanitize_text(str(item), 300) for item in data.get("verification_plan", []) if str(item).strip()
            ],
            "source": "ai",
        }
    except Exception:
        return {
            "remediation_summary": "Apply principle-of-least-privilege controls and strict input/output validation for the affected workflow.",
            "fix_steps": [
                "Enforce server-side authorization and access controls for all affected endpoints.",
                "Add validation and canonicalization checks for user-controllable input.",
                "Instrument logging and alerting for repeated anomalous access patterns.",
            ],
            "verification_plan": [
                "Run regression tests for the vulnerable request pattern.",
                "Re-run authorized security checks in staging and production-like environments.",
            ],
            "source": "fallback",
        }


async def generate_report(
    context: dict[str, Any],
    platform: str,
    organization_id: str | None = None,
) -> dict[str, Any]:
    """
    Build a platform-aware, deterministic report payload for human review.
    """
    platform_name = _normalize_platform(platform)
    mapped_severity = _map_severity_to_platform(context.get("severity"), platform_name)

    reproduction = await generate_reproduction_steps(context, organization_id=organization_id)
    impact = await generate_business_impact({**context, "severity": mapped_severity}, organization_id=organization_id)
    remediation = await generate_remediation(context, organization_id=organization_id)

    title = _sanitize_text(context.get("title"), 255) or "Untitled Vulnerability"
    affected_asset = _sanitize_text(context.get("affected_asset") or context.get("endpoint"), 1000)
    summary = _sanitize_text(context.get("summary") or context.get("description"), 2500)
    technical_details = _sanitize_text(context.get("technical_details") or context.get("description"), 6000)
    evidence = _sanitize_text(context.get("evidence"), 4000)

    references = context.get("references") or []
    safe_references = [_sanitize_text(str(item), 500) for item in references if str(item).strip()]

    return {
        "platform": platform_name,
        "title": title,
        "severity": mapped_severity,
        "summary": summary,
        "affected_asset": affected_asset,
        "steps_to_reproduce": reproduction.get("steps", []),
        "technical_details": technical_details,
        "business_impact": impact.get("impact_summary", ""),
        "impact_workflows": impact.get("impacted_workflows", []),
        "evidence": evidence,
        "remediation": remediation.get("remediation_summary", ""),
        "remediation_steps": remediation.get("fix_steps", []),
        "verification_plan": remediation.get("verification_plan", []),
        "references": safe_references,
        "human_review_required": True,
        "advisory_only": True,
        "factual_source": "finding_and_triage_context",
    }
