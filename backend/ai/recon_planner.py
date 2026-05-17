"""
AI-assisted recon planning engine.

All outputs are advisory-only — no autonomous execution occurs.
Human approval is required before any recon action is initiated.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from backend.ai.client import generate_completion, AIClientError

logger = logging.getLogger(__name__)

_RECON_PLAN_SYSTEM = (
    "You are a defensive security recon planning assistant. "
    "Recommend recon strategies for authorized security assessments only. "
    "All recommendations are advisory. Never recommend autonomous exploitation "
    "or shell command execution. Respond ONLY with valid JSON."
)

_RECON_PLAN_TEMPLATE = (
    "Generate a structured recon plan.\n\n"
    "CONTEXT:\n"
    "- Asset Count: {asset_count}\n"
    "- Technologies: {technologies}\n"
    "- Active Exposures: {active_exposures}\n"
    "- Risk Distribution: {risk_distribution}\n"
    "- Recent Findings: {recent_findings}\n"
    "- Scope Domains: {scope_domains}\n\n"
    "Return JSON with keys: plan_name, objective, phases (list of "
    "{{phase_name,priority,scan_types,rationale,estimated_duration_minutes}}), "
    "focus_areas, risk_notes, confidence. Respond ONLY with valid JSON."
)

_ASSET_CONTEXT_TEMPLATE = (
    "Analyze this asset for recon prioritization.\n\n"
    "ASSET:\n"
    "- Hostname: {hostname}\n"
    "- Technologies: {technologies}\n"
    "- Exposure Count: {exposure_count}\n"
    "- Risk Score: {risk_score}\n"
    "- Internet Facing: {is_internet_facing}\n"
    "- Finding Count: {finding_count}\n"
    "- Last Seen: {last_seen}\n\n"
    "Return JSON with keys: recon_priority (critical|high|medium|low), "
    "priority_rationale, recommended_scans, attack_vectors_of_interest, "
    "notes, confidence. Respond ONLY with valid JSON."
)

_SCAN_STRATEGY_TEMPLATE = (
    "Recommend a scan strategy.\n\n"
    "TARGET:\n"
    "- Asset Type: {asset_type}\n"
    "- Technologies: {technologies}\n"
    "- Exposures: {exposure_types}\n"
    "- Previous Coverage: {scan_coverage}\n"
    "- Risk Level: {risk_level}\n\n"
    "Return JSON with keys: strategy_name, scan_sequence (list of "
    "{{step,tool_category,purpose,scope_constraint}}), do_not_scan, "
    "expected_findings_types, confidence. Respond ONLY with valid JSON."
)


def _sanitize(value: Any, max_len: int = 200) -> str:
    text = str(value) if value is not None else "unknown"
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    return text[:max_len]


def _sanitize_list(values: List[Any], max_items: int = 10, max_item_len: int = 100) -> str:
    safe = [_sanitize(v, max_item_len) for v in (values or [])[:max_items]]
    return ", ".join(safe) if safe else "none"


def _parse_ai_json(raw: dict, required_keys: List[str]) -> Dict[str, Any]:
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
        raise ValueError(f"AI response missing keys: {missing}")
    return parsed


async def generate_recon_plan(
    *,
    asset_count: int,
    technologies: List[str],
    active_exposures: int,
    risk_distribution: Dict[str, int],
    recent_findings: int,
    scope_domains: List[str],
    organization_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Generate AI-assisted recon plan. Advisory-only — requires human approval."""
    prompt = _RECON_PLAN_TEMPLATE.format(
        asset_count=asset_count,
        technologies=_sanitize_list(technologies),
        active_exposures=active_exposures,
        risk_distribution=_sanitize(json.dumps(risk_distribution)),
        recent_findings=recent_findings,
        scope_domains=_sanitize_list(scope_domains, max_items=5),
    )
    try:
        raw = await generate_completion(f"{_RECON_PLAN_SYSTEM}\n\n{prompt}", temperature=0.1)
        plan = _parse_ai_json(raw, ["plan_name", "objective", "phases", "focus_areas", "confidence"])
    except (AIClientError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Recon plan AI failed (%s); using fallback", exc)
        plan = _fallback_recon_plan(asset_count, active_exposures, technologies)

    plan.update({
        "generated_at": datetime.utcnow().isoformat(),
        "organization_id": str(organization_id) if organization_id else None,
        "advisory_note": "AI-generated advisory plan. Human review and approval required.",
    })
    return plan


async def analyze_asset_context(
    *,
    hostname: str,
    technologies: List[str],
    exposure_count: int,
    risk_score: float,
    is_internet_facing: bool,
    finding_count: int,
    last_seen: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Analyze a single asset for recon prioritization. Advisory-only."""
    prompt = _ASSET_CONTEXT_TEMPLATE.format(
        hostname=_sanitize(hostname, 100),
        technologies=_sanitize_list(technologies),
        exposure_count=exposure_count,
        risk_score=round(risk_score, 2),
        is_internet_facing=is_internet_facing,
        finding_count=finding_count,
        last_seen=_sanitize(last_seen.isoformat() if last_seen else "unknown"),
    )
    try:
        raw = await generate_completion(f"{_RECON_PLAN_SYSTEM}\n\n{prompt}", temperature=0.1)
        analysis = _parse_ai_json(raw, ["recon_priority", "recommended_scans", "confidence"])
    except (AIClientError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Asset context AI failed (%s); using fallback", exc)
        analysis = _fallback_asset_analysis(risk_score, exposure_count, is_internet_facing)

    analysis.update({
        "hostname": _sanitize(hostname, 100),
        "analyzed_at": datetime.utcnow().isoformat(),
        "advisory_note": "AI analysis — advisory only. Requires human approval.",
    })
    return analysis


async def recommend_scan_strategy(
    *,
    asset_type: str,
    technologies: List[str],
    exposure_types: List[str],
    scan_coverage: List[str],
    risk_level: str,
) -> Dict[str, Any]:
    """Recommend scan strategy. Advisory-only — no autonomous execution."""
    prompt = _SCAN_STRATEGY_TEMPLATE.format(
        asset_type=_sanitize(asset_type),
        technologies=_sanitize_list(technologies),
        exposure_types=_sanitize_list(exposure_types),
        scan_coverage=_sanitize_list(scan_coverage),
        risk_level=_sanitize(risk_level),
    )
    try:
        raw = await generate_completion(f"{_RECON_PLAN_SYSTEM}\n\n{prompt}", temperature=0.1)
        strategy = _parse_ai_json(raw, ["strategy_name", "scan_sequence", "confidence"])
    except (AIClientError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Scan strategy AI failed (%s); using fallback", exc)
        strategy = _fallback_scan_strategy(asset_type, risk_level)

    strategy.update({
        "generated_at": datetime.utcnow().isoformat(),
        "requires_human_approval": True,
        "advisory_note": "AI-recommended strategy. No automated execution. Human must approve each step.",
    })
    return strategy


def _fallback_recon_plan(asset_count: int, active_exposures: int, technologies: List[str]) -> Dict[str, Any]:
    return {
        "plan_name": "Standard Recon Plan (Fallback)",
        "objective": "Enumerate attack surface and identify high-value recon targets",
        "phases": [
            {"phase_name": "Asset Discovery", "priority": 1,
             "scan_types": ["subdomain_enumeration", "dns_resolution", "httpx_probe"],
             "rationale": "Establish full asset inventory", "estimated_duration_minutes": 30},
            {"phase_name": "Technology Fingerprinting", "priority": 2,
             "scan_types": ["header_analysis", "tech_detection"],
             "rationale": "Identify technology stack", "estimated_duration_minutes": 20},
            {"phase_name": "Vulnerability Scanning", "priority": 3,
             "scan_types": ["nuclei_scan", "exposure_detection"],
             "rationale": f"{active_exposures} active exposures require investigation",
             "estimated_duration_minutes": 45},
        ],
        "focus_areas": technologies[:5] if technologies else ["web_application"],
        "risk_notes": [f"{active_exposures} active exposures", f"{asset_count} assets in scope"],
        "confidence": 0.5,
    }


def _fallback_asset_analysis(risk_score: float, exposure_count: int, is_internet_facing: bool) -> Dict[str, Any]:
    if risk_score >= 70 or exposure_count >= 5:
        priority, scans = "critical", ["full_port_scan", "nuclei_scan", "header_analysis", "dir_bruteforce"]
    elif risk_score >= 40 or is_internet_facing:
        priority, scans = "high", ["web_crawl", "nuclei_scan", "header_analysis"]
    else:
        priority, scans = "medium", ["httpx_probe", "header_analysis"]
    return {
        "recon_priority": priority,
        "priority_rationale": f"Risk score {risk_score:.1f}, {exposure_count} exposures",
        "recommended_scans": scans,
        "attack_vectors_of_interest": ["exposed_endpoints", "outdated_components"],
        "notes": "Fallback analysis — AI unavailable",
        "confidence": 0.5,
    }


def _fallback_scan_strategy(asset_type: str, risk_level: str) -> Dict[str, Any]:
    steps = [
        {"step": 1, "tool_category": "httpx_probe", "purpose": "Confirm liveness", "scope_constraint": "In-scope domains only"},
        {"step": 2, "tool_category": "web_crawl", "purpose": "Discover endpoints", "scope_constraint": "In-scope paths only"},
        {"step": 3, "tool_category": "header_analysis", "purpose": "Check security headers", "scope_constraint": "Passive only"},
        {"step": 4, "tool_category": "vuln_scan", "purpose": "Identify known vulnerabilities", "scope_constraint": "Approved templates only"},
    ]
    return {
        "strategy_name": f"{asset_type.title()} Recon Strategy (Fallback)",
        "scan_sequence": steps,
        "do_not_scan": ["out-of-scope domains", "third-party services"],
        "expected_findings_types": ["misconfigurations", "outdated_components", "weak_headers"],
        "confidence": 0.5,
    }
