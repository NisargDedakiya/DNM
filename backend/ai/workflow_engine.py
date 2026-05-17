"""
Adaptive AI workflow engine for recon pipeline orchestration.

Builds human-approved recon workflow graphs, recommends next stages,
and optimizes scan pipelines. All workflows require explicit human approval
before execution. No autonomous actions are taken.
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

_WORKFLOW_SYSTEM = (
    "You are a defensive security workflow advisor. "
    "Design recon workflows for authorized assessments only. "
    "Every stage requires human approval before execution. "
    "Never recommend autonomous exploitation or unsupervised scanning. "
    "Respond ONLY with valid JSON."
)

_BUILD_WORKFLOW_TEMPLATE = (
    "Build a recon workflow pipeline.\n\n"
    "CONTEXT:\n"
    "- Program Name: {program_name}\n"
    "- Scope Domains: {scope_domains}\n"
    "- Asset Types: {asset_types}\n"
    "- Risk Level: {risk_level}\n"
    "- Known Technologies: {technologies}\n"
    "- Existing Coverage: {existing_coverage}\n\n"
    "Return JSON with keys: workflow_name, description, stages (list of "
    "{{stage_id,stage_name,dependencies,tool_category,inputs_required,"
    "outputs_produced,requires_approval,estimated_minutes}}), "
    "total_estimated_minutes, confidence. Respond ONLY with valid JSON."
)

_NEXT_STAGE_TEMPLATE = (
    "Recommend the next recon stage.\n\n"
    "COMPLETED STAGES: {completed_stages}\n"
    "CURRENT FINDINGS: {current_findings}\n"
    "ASSET STATE: {asset_state}\n"
    "RISK LEVEL: {risk_level}\n\n"
    "Return JSON with keys: recommended_stage, stage_name, rationale, "
    "tool_category, priority (1-3), confidence, skip_if. "
    "Respond ONLY with valid JSON."
)

_OPTIMIZE_PIPELINE_TEMPLATE = (
    "Optimize this recon pipeline for efficiency.\n\n"
    "CURRENT PIPELINE: {pipeline_stages}\n"
    "RESOURCE CONSTRAINTS: {constraints}\n"
    "PRIORITY TARGETS: {priority_targets}\n"
    "PAST PERFORMANCE: {past_performance}\n\n"
    "Return JSON with keys: optimized_stages (reordered list with same schema), "
    "removed_stages (list with reason), parallel_groups (list of stage_id lists "
    "that can run simultaneously), optimization_rationale, time_saved_estimate_minutes, "
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


async def build_workflow(
    *,
    program_name: str,
    scope_domains: List[str],
    asset_types: List[str],
    risk_level: str,
    technologies: List[str],
    existing_coverage: List[str],
    program_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """
    Build an adaptive recon workflow pipeline.

    All stages are marked requires_approval=True. No autonomous execution.

    Args:
        program_name: Name of the recon program
        scope_domains: In-scope domain list
        asset_types: Detected asset types
        risk_level: Current aggregate risk level
        technologies: Known technologies
        existing_coverage: Already-executed scan types
        program_id: Optional program UUID

    Returns:
        dict: Workflow with ordered stages, dependencies, approval requirements
    """
    prompt = _BUILD_WORKFLOW_TEMPLATE.format(
        program_name=_sanitize(program_name, 100),
        scope_domains=_sanitize_list(scope_domains, max_items=5),
        asset_types=_sanitize_list(asset_types),
        risk_level=_sanitize(risk_level),
        technologies=_sanitize_list(technologies),
        existing_coverage=_sanitize_list(existing_coverage),
    )
    try:
        raw = await generate_completion(f"{_WORKFLOW_SYSTEM}\n\n{prompt}", temperature=0.1)
        workflow = _parse_json(raw, ["workflow_name", "stages", "confidence"])
    except (AIClientError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Workflow build AI failed (%s); using fallback", exc)
        workflow = _fallback_workflow(program_name, scope_domains, risk_level)

    # Enforce approval requirement on every stage
    for stage in workflow.get("stages", []):
        stage["requires_approval"] = True

    workflow.update({
        "generated_at": datetime.utcnow().isoformat(),
        "program_id": str(program_id) if program_id else None,
        "status": "pending_review",
        "advisory_note": "All workflow stages require human approval before execution.",
    })
    return workflow


async def recommend_next_stage(
    *,
    completed_stages: List[str],
    current_findings: Dict[str, Any],
    asset_state: Dict[str, Any],
    risk_level: str,
) -> Dict[str, Any]:
    """
    Recommend the next optimal recon stage based on current progress.

    Args:
        completed_stages: List of completed stage names
        current_findings: Summary of findings so far
        asset_state: Current asset intelligence summary
        risk_level: Current risk assessment

    Returns:
        dict: Next stage recommendation with rationale (advisory only)
    """
    prompt = _NEXT_STAGE_TEMPLATE.format(
        completed_stages=_sanitize_list(completed_stages),
        current_findings=_sanitize(json.dumps(current_findings), 300),
        asset_state=_sanitize(json.dumps(asset_state), 300),
        risk_level=_sanitize(risk_level),
    )
    try:
        raw = await generate_completion(f"{_WORKFLOW_SYSTEM}\n\n{prompt}", temperature=0.1)
        recommendation = _parse_json(raw, ["recommended_stage", "rationale", "confidence"])
    except (AIClientError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Next stage AI failed (%s); using fallback", exc)
        recommendation = _fallback_next_stage(completed_stages, risk_level)

    recommendation.update({
        "generated_at": datetime.utcnow().isoformat(),
        "requires_human_approval": True,
        "advisory_note": "Stage recommendation is advisory. Human must approve before execution.",
    })
    return recommendation


async def optimize_scan_pipeline(
    *,
    pipeline_stages: List[Dict[str, Any]],
    constraints: Dict[str, Any],
    priority_targets: List[str],
    past_performance: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Optimize an existing scan pipeline for efficiency and coverage.

    Args:
        pipeline_stages: Current pipeline stage definitions
        constraints: Resource constraints (time, concurrency, rate_limits)
        priority_targets: High-value targets to prioritize
        past_performance: Historical scan timing/results data

    Returns:
        dict: Optimized pipeline with parallel groups and rationale
    """
    prompt = _OPTIMIZE_PIPELINE_TEMPLATE.format(
        pipeline_stages=_sanitize(json.dumps(pipeline_stages), 500),
        constraints=_sanitize(json.dumps(constraints), 200),
        priority_targets=_sanitize_list(priority_targets),
        past_performance=_sanitize(json.dumps(past_performance), 200),
    )
    try:
        raw = await generate_completion(f"{_WORKFLOW_SYSTEM}\n\n{prompt}", temperature=0.1)
        optimized = _parse_json(raw, ["optimized_stages", "confidence"])
    except (AIClientError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Pipeline optimization AI failed (%s); using fallback", exc)
        optimized = _fallback_optimize(pipeline_stages)

    # Enforce approval on all optimized stages
    for stage in optimized.get("optimized_stages", []):
        stage["requires_approval"] = True

    optimized.update({
        "optimized_at": datetime.utcnow().isoformat(),
        "advisory_note": "Optimized pipeline is advisory. All stages require human approval.",
    })
    return optimized


# ── Fallbacks ───────────────────────────────────────────────

def _fallback_workflow(program_name: str, scope_domains: List[str], risk_level: str) -> Dict[str, Any]:
    return {
        "workflow_name": f"{program_name} Recon Workflow (Fallback)",
        "description": "Standard recon workflow for authorized security assessment",
        "stages": [
            {
                "stage_id": "s1", "stage_name": "Subdomain Enumeration",
                "dependencies": [], "tool_category": "subdomain_enumeration",
                "inputs_required": ["scope_domains"], "outputs_produced": ["subdomain_list"],
                "requires_approval": True, "estimated_minutes": 15,
            },
            {
                "stage_id": "s2", "stage_name": "HTTP Probing",
                "dependencies": ["s1"], "tool_category": "httpx_probe",
                "inputs_required": ["subdomain_list"], "outputs_produced": ["live_hosts"],
                "requires_approval": True, "estimated_minutes": 10,
            },
            {
                "stage_id": "s3", "stage_name": "Technology Fingerprinting",
                "dependencies": ["s2"], "tool_category": "tech_detection",
                "inputs_required": ["live_hosts"], "outputs_produced": ["tech_profile"],
                "requires_approval": True, "estimated_minutes": 10,
            },
            {
                "stage_id": "s4", "stage_name": "Web Crawl",
                "dependencies": ["s2"], "tool_category": "web_crawl",
                "inputs_required": ["live_hosts"], "outputs_produced": ["endpoint_list"],
                "requires_approval": True, "estimated_minutes": 20,
            },
            {
                "stage_id": "s5", "stage_name": "Vulnerability Scan",
                "dependencies": ["s3", "s4"], "tool_category": "vuln_scan",
                "inputs_required": ["endpoint_list", "tech_profile"],
                "outputs_produced": ["findings"], "requires_approval": True,
                "estimated_minutes": 30,
            },
        ],
        "total_estimated_minutes": 85,
        "confidence": 0.5,
    }


def _fallback_next_stage(completed: List[str], risk_level: str) -> Dict[str, Any]:
    stage_sequence = [
        "subdomain_enumeration", "httpx_probe", "tech_detection",
        "web_crawl", "vuln_scan", "report_generation"
    ]
    next_stage = next(
        (s for s in stage_sequence if s not in completed),
        "report_generation"
    )
    return {
        "recommended_stage": next_stage,
        "stage_name": next_stage.replace("_", " ").title(),
        "rationale": f"Sequential recon progression after {len(completed)} completed stages",
        "tool_category": next_stage,
        "priority": 2,
        "confidence": 0.5,
        "skip_if": "already_covered",
    }


def _fallback_optimize(pipeline_stages: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "optimized_stages": pipeline_stages,
        "removed_stages": [],
        "parallel_groups": [],
        "optimization_rationale": "Fallback — AI unavailable, pipeline unchanged",
        "time_saved_estimate_minutes": 0,
        "confidence": 0.5,
    }
