"""
AI recommendation engine for recon next-action suggestions.

Provides findings-aware, exposure-aware, and asset-prioritization
recommendations. All outputs are advisory — no autonomous actions taken.
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

_REC_SYSTEM = (
    "You are a defensive security recommendation advisor. "
    "Suggest recon and security actions for authorized assessments only. "
    "All recommendations are advisory and require human approval. "
    "Never suggest autonomous exploitation. Respond ONLY with valid JSON."
)

_NEXT_ACTIONS_TEMPLATE = (
    "Recommend next security actions.\n\n"
    "CONTEXT:\n"
    "- Active Findings: {active_findings}\n"
    "- Critical Exposures: {critical_exposures}\n"
    "- High Risk Assets: {high_risk_assets}\n"
    "- Last Scan Date: {last_scan_date}\n"
    "- Unscanned Assets: {unscanned_assets}\n"
    "- Technology Stack: {technology_stack}\n\n"
    "Return JSON with keys: recommendations (list of "
    "{{action_id,action_type,title,rationale,priority(1-5),"
    "effort_estimate,expected_impact}}), "
    "immediate_priorities, confidence. Respond ONLY with valid JSON."
)

_ASSET_FOCUS_TEMPLATE = (
    "Recommend which assets to focus recon efforts on.\n\n"
    "ASSETS SUMMARY:\n"
    "- Total Assets: {total_assets}\n"
    "- Exposure Distribution: {exposure_distribution}\n"
    "- Technology Mix: {technology_mix}\n"
    "- Recent Activity: {recent_activity}\n"
    "- Uncovered Assets: {uncovered_assets}\n\n"
    "Return JSON with keys: focus_assets (list of "
    "{{asset_identifier,focus_reason,priority(critical|high|medium|low),"
    "recommended_actions}}), "
    "deprioritize_assets, focus_rationale, confidence. "
    "Respond ONLY with valid JSON."
)

_FOLLOWUP_SCAN_TEMPLATE = (
    "Recommend follow-up scans based on current findings.\n\n"
    "FINDINGS:\n"
    "- Finding Types: {finding_types}\n"
    "- Severity Counts: {severity_counts}\n"
    "- Affected Assets: {affected_assets}\n"
    "- Technologies Involved: {technologies}\n"
    "- Scan Gaps: {scan_gaps}\n\n"
    "Return JSON with keys: followup_scans (list of "
    "{{scan_type,target_assets,rationale,expected_findings,"
    "priority(1-3),scope_constraint}}), "
    "confidence. Respond ONLY with valid JSON."
)


def _sanitize(value: Any, max_len: int = 200) -> str:
    text = str(value) if value is not None else "unknown"
    return re.sub(r"[\x00-\x1f\x7f]", " ", text)[:max_len]


def _sanitize_list(values: List[Any], max_items: int = 10, max_item_len: int = 100) -> str:
    safe = [_sanitize(v, max_item_len) for v in (values or [])[:max_items]]
    return ", ".join(safe) if safe else "none"


def _parse_json(raw: dict, required_keys: List[str]) -> Dict[str, Any]:
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


async def recommend_next_actions(
    *,
    active_findings: int,
    critical_exposures: int,
    high_risk_assets: int,
    last_scan_date: Optional[datetime],
    unscanned_assets: int,
    technology_stack: List[str],
    organization_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """
    Generate prioritized next-action recommendations.

    Args:
        active_findings: Count of unresolved findings
        critical_exposures: Count of critical-severity exposures
        high_risk_assets: Count of high-risk scored assets
        last_scan_date: When last scan was run
        unscanned_assets: Assets with no scan history
        technology_stack: Detected technology names
        organization_id: Optional org UUID

    Returns:
        dict: Prioritized action list — advisory only, requires human approval
    """
    prompt = _NEXT_ACTIONS_TEMPLATE.format(
        active_findings=active_findings,
        critical_exposures=critical_exposures,
        high_risk_assets=high_risk_assets,
        last_scan_date=_sanitize(last_scan_date.isoformat() if last_scan_date else "never"),
        unscanned_assets=unscanned_assets,
        technology_stack=_sanitize_list(technology_stack),
    )
    try:
        raw = await generate_completion(f"{_REC_SYSTEM}\n\n{prompt}", temperature=0.1)
        result = _parse_json(raw, ["recommendations", "immediate_priorities", "confidence"])
    except (AIClientError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Next-actions AI failed (%s); using fallback", exc)
        result = _fallback_next_actions(active_findings, critical_exposures, unscanned_assets)

    result.update({
        "generated_at": datetime.utcnow().isoformat(),
        "organization_id": str(organization_id) if organization_id else None,
        "advisory_note": "All recommendations are advisory and require human approval.",
    })
    return result


async def recommend_asset_focus(
    *,
    total_assets: int,
    exposure_distribution: Dict[str, int],
    technology_mix: List[str],
    recent_activity: Dict[str, Any],
    uncovered_assets: int,
    organization_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """
    Recommend which assets should receive focused recon attention.

    Args:
        total_assets: Total asset count
        exposure_distribution: Dict of risk_level -> count
        technology_mix: Technology names across all assets
        recent_activity: Dict summary of recent scan/finding activity
        uncovered_assets: Count of assets with no recon history
        organization_id: Optional org UUID

    Returns:
        dict: Asset focus recommendations with priority tiers
    """
    prompt = _ASSET_FOCUS_TEMPLATE.format(
        total_assets=total_assets,
        exposure_distribution=_sanitize(json.dumps(exposure_distribution), 300),
        technology_mix=_sanitize_list(technology_mix),
        recent_activity=_sanitize(json.dumps(recent_activity), 200),
        uncovered_assets=uncovered_assets,
    )
    try:
        raw = await generate_completion(f"{_REC_SYSTEM}\n\n{prompt}", temperature=0.1)
        result = _parse_json(raw, ["focus_assets", "confidence"])
    except (AIClientError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Asset focus AI failed (%s); using fallback", exc)
        result = _fallback_asset_focus(total_assets, exposure_distribution, uncovered_assets)

    result.update({
        "generated_at": datetime.utcnow().isoformat(),
        "organization_id": str(organization_id) if organization_id else None,
        "advisory_note": "Asset focus recommendations are advisory. Human review required.",
    })
    return result


async def recommend_followup_scans(
    *,
    finding_types: List[str],
    severity_counts: Dict[str, int],
    affected_assets: List[str],
    technologies: List[str],
    scan_gaps: List[str],
    program_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """
    Recommend follow-up scans based on current findings and gaps.

    Args:
        finding_types: Types of findings discovered
        severity_counts: Dict of severity -> count
        affected_assets: Asset identifiers with findings
        technologies: Technology stack involved
        scan_gaps: Areas not yet covered by recon
        program_id: Optional program UUID

    Returns:
        dict: Follow-up scan recommendations with scope constraints
    """
    prompt = _FOLLOWUP_SCAN_TEMPLATE.format(
        finding_types=_sanitize_list(finding_types),
        severity_counts=_sanitize(json.dumps(severity_counts), 200),
        affected_assets=_sanitize_list(affected_assets, max_items=5),
        technologies=_sanitize_list(technologies),
        scan_gaps=_sanitize_list(scan_gaps),
    )
    try:
        raw = await generate_completion(f"{_REC_SYSTEM}\n\n{prompt}", temperature=0.1)
        result = _parse_json(raw, ["followup_scans", "confidence"])
    except (AIClientError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Follow-up scan AI failed (%s); using fallback", exc)
        result = _fallback_followup(finding_types, severity_counts)

    result.update({
        "generated_at": datetime.utcnow().isoformat(),
        "program_id": str(program_id) if program_id else None,
        "requires_human_approval": True,
        "advisory_note": "Scan recommendations are advisory. Scope constraints must be enforced.",
    })
    return result


# ── Fallbacks ────────────────────────────────────────────────

def _fallback_next_actions(
    active_findings: int, critical_exposures: int, unscanned_assets: int
) -> Dict[str, Any]:
    recs = []
    if critical_exposures > 0:
        recs.append({
            "action_id": "a1", "action_type": "remediate_exposure",
            "title": f"Remediate {critical_exposures} critical exposures",
            "rationale": "Critical exposures represent highest risk surface",
            "priority": 1, "effort_estimate": "high", "expected_impact": "critical_risk_reduction",
        })
    if active_findings > 0:
        recs.append({
            "action_id": "a2", "action_type": "triage_findings",
            "title": f"Triage {active_findings} active findings",
            "rationale": "Unresolved findings may contain exploitable vulnerabilities",
            "priority": 2, "effort_estimate": "medium", "expected_impact": "finding_resolution",
        })
    if unscanned_assets > 0:
        recs.append({
            "action_id": "a3", "action_type": "scan_uncovered",
            "title": f"Scan {unscanned_assets} uncovered assets",
            "rationale": "Uncovered assets represent blind spots in attack surface",
            "priority": 3, "effort_estimate": "medium", "expected_impact": "coverage_improvement",
        })
    return {
        "recommendations": recs,
        "immediate_priorities": [r["title"] for r in recs[:2]],
        "confidence": 0.5,
    }


def _fallback_asset_focus(
    total_assets: int,
    exposure_distribution: Dict[str, int],
    uncovered_assets: int,
) -> Dict[str, Any]:
    critical_count = exposure_distribution.get("critical", 0)
    return {
        "focus_assets": [
            {
                "asset_identifier": "high_exposure_assets",
                "focus_reason": f"{critical_count} critical exposures detected",
                "priority": "critical" if critical_count > 0 else "high",
                "recommended_actions": ["deep_scan", "exposure_validation"],
            }
        ],
        "deprioritize_assets": ["recently_scanned_clean_assets"],
        "focus_rationale": f"{uncovered_assets} of {total_assets} assets uncovered",
        "confidence": 0.5,
    }


def _fallback_followup(
    finding_types: List[str],
    severity_counts: Dict[str, int],
) -> Dict[str, Any]:
    scans = []
    if "xss" in " ".join(finding_types).lower():
        scans.append({
            "scan_type": "xss_deep_scan", "target_assets": ["web_frontends"],
            "rationale": "XSS findings warrant deeper parameter fuzzing",
            "expected_findings": ["stored_xss", "dom_xss"],
            "priority": 1, "scope_constraint": "In-scope assets only",
        })
    if severity_counts.get("critical", 0) > 0:
        scans.append({
            "scan_type": "critical_path_retest", "target_assets": ["affected_assets"],
            "rationale": "Critical findings require retest for confirmation",
            "expected_findings": ["reconfirmed_criticals"],
            "priority": 1, "scope_constraint": "Confirmed in-scope only",
        })
    if not scans:
        scans.append({
            "scan_type": "general_vuln_scan", "target_assets": ["all_in_scope"],
            "rationale": "Standard follow-up coverage",
            "expected_findings": ["misconfigurations", "outdated_components"],
            "priority": 3, "scope_constraint": "In-scope assets only",
        })
    return {"followup_scans": scans, "confidence": 0.5}
