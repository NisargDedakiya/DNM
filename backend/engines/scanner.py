"""
Advanced scanner orchestrator for high-signal recon pipeline.

Pipeline:
subfinder -> httpx -> fingerprint strategy -> targeted nuclei -> JS/API intelligence
-> katana -> dalfox -> ffuf -> optional sqlmap (approval only)
"""
from __future__ import annotations

from typing import Any

from backend.engines.dalfox_engine import run_dalfox_scan
from backend.engines.ffuf_engine import run_ffuf_scan
from backend.engines.nuclei_engine import run_targeted_nuclei_scan
from backend.engines.sqlmap_engine import run_sqlmap_scan
from backend.scanners.httpx_scanner import HttpxScanner
from backend.scanners.katana_scanner import KatanaScanner
from backend.scanners.subfinder_scanner import SubfinderScanner
from backend.services.api_surface_service import APISurfaceService
from backend.services.fingerprint_scan_service import FingerprintScanService
from backend.services.js_intelligence_service import JSIntelligenceService
from backend.utils.approval_gate import validate_scan_execution
from backend.utils.scope_validator import validate_target


async def validate_scan_workflow(
    *,
    target: str,
    scope_rules: list[str],
    include_sqlmap: bool,
    sqlmap_approved: bool,
) -> dict[str, Any]:
    """Validate scope and risky workflow approvals before execution."""
    scope_check = validate_target(target, scope_rules)
    if not scope_check["authorized"]:
        return {
            "allowed": False,
            "reason": "target_out_of_scope",
            "scope": scope_check,
        }

    if include_sqlmap:
        sqlmap_policy = validate_scan_execution(
            scanner_name="sqlmap",
            approved_by_human=sqlmap_approved,
            authenticated_scan=False,
            aggressive_fuzzing=False,
            crawl_depth=1,
            target_count=1,
            within_scope=True,
        )
        if not sqlmap_policy["allowed"]:
            return {
                "allowed": False,
                "reason": sqlmap_policy["reason"],
                "scope": scope_check,
                "sqlmap_policy": sqlmap_policy,
            }

    return {
        "allowed": True,
        "reason": "workflow_valid",
        "scope": scope_check,
    }


async def dispatch_scan_stage(stage: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one pipeline stage to scanner/service implementation."""
    if stage == "subfinder":
        scanner = SubfinderScanner(timeout=payload.get("timeout", 180))
        return await scanner.run(payload["target"])

    if stage == "httpx":
        scanner = HttpxScanner(timeout=payload.get("timeout", 180))
        return await scanner.run(payload["target"], targets_file=payload.get("targets_file"))

    if stage == "katana":
        scanner = KatanaScanner(timeout=payload.get("timeout", 180))
        return await scanner.run(payload["target"])

    if stage == "nuclei":
        return await run_targeted_nuclei_scan(
            target=payload["target"],
            fingerprints=payload.get("fingerprints", []),
            severity=payload.get("severity", "high"),
            timeout=payload.get("timeout", 240),
        )

    if stage == "dalfox":
        return await run_dalfox_scan(
            urls=payload.get("urls", []),
            timeout=payload.get("timeout", 180),
            max_targets=payload.get("max_targets", 25),
        )

    if stage == "ffuf":
        return await run_ffuf_scan(
            urls=payload.get("urls", []),
            timeout=payload.get("timeout", 180),
            max_targets=payload.get("max_targets", 20),
        )

    if stage == "sqlmap":
        return await run_sqlmap_scan(
            target=payload["target"],
            scope_rules=payload["scope_rules"],
            approval_token=payload.get("approval_token"),
            approved_by_human=payload.get("approved_by_human", False),
            timeout=payload.get("timeout", 180),
        )

    raise ValueError(f"Unknown scan stage: {stage}")


def process_scan_results(results: dict[str, Any]) -> dict[str, Any]:
    """Aggregate stage outputs into high-signal findings and recon actions."""
    nuclei_findings = results.get("nuclei", {}).get("findings", [])
    dalfox_findings = results.get("dalfox", {}).get("findings", [])
    ffuf_results = results.get("ffuf", {}).get("results", [])

    high_signal = [
        f for f in nuclei_findings
        if str(f.get("severity", "")).lower() in {"critical", "high"}
    ]

    if dalfox_findings:
        high_signal.extend(
            {
                "title": "Potential XSS signal",
                "severity": "high",
                "endpoint": item.get("target"),
                "raw": item,
            }
            for item in dalfox_findings[:20]
        )

    if ffuf_results:
        for item in ffuf_results[:20]:
            if item.get("matches"):
                high_signal.append(
                    {
                        "title": "Interesting hidden endpoint discovered",
                        "severity": "medium",
                        "endpoint": item.get("target"),
                        "raw": item,
                    }
                )

    return {
        "high_signal_findings": high_signal,
        "findings_count": len(high_signal),
        "raw_stage_results": results,
    }


async def run_scan_pipeline(
    *,
    target: str,
    scope_rules: list[str],
    fingerprint_data: list[str] | None = None,
    js_assets: list[dict[str, Any]] | None = None,
    include_sqlmap: bool = False,
    sqlmap_approved: bool = False,
    sqlmap_approval_token: str | None = None,
) -> dict[str, Any]:
    """Run full high-signal recon pipeline with safety controls."""
    workflow = await validate_scan_workflow(
        target=target,
        scope_rules=scope_rules,
        include_sqlmap=include_sqlmap,
        sqlmap_approved=sqlmap_approved,
    )
    if not workflow["allowed"]:
        return {"status": "blocked", "reason": workflow["reason"], "workflow": workflow}

    results: dict[str, Any] = {}

    subfinder = await dispatch_scan_stage("subfinder", {"target": target})
    results["subfinder"] = subfinder

    # Use base target if subfinder has no output.
    discovered_targets = subfinder.get("results") or [workflow["scope"]["normalized_target"]]

    # Probe first discovered target for orchestration simplicity.
    httpx = await dispatch_scan_stage("httpx", {"target": discovered_targets[0]})
    results["httpx"] = httpx

    fp_service = FingerprintScanService()
    strategy = fp_service.generate_scan_strategy(
        [
            {
                "target": discovered_targets[0],
                "fingerprints": fingerprint_data or [],
                "internet_facing": True,
            }
        ]
    )
    results["fingerprint_strategy"] = strategy

    nuclei = await dispatch_scan_stage(
        "nuclei",
        {
            "target": discovered_targets[0],
            "fingerprints": fingerprint_data or [],
            "severity": "high",
        },
    )
    results["nuclei"] = nuclei

    js_service = JSIntelligenceService()
    js_analysis = js_service.analyze_javascript(js_assets or [])
    results["js_intelligence"] = js_analysis

    api_service = APISurfaceService()
    api_surface = api_service.detect_api_surfaces(js_analysis.get("extracted_endpoints", []))
    api_risk = api_service.analyze_api_risk(api_surface)
    results["api_surface"] = api_surface
    results["api_risk"] = api_risk

    katana = await dispatch_scan_stage("katana", {"target": discovered_targets[0]})
    results["katana"] = katana

    urls_for_active_scans = katana.get("endpoints", [])
    if not urls_for_active_scans and httpx.get("results"):
        urls_for_active_scans = [
            r.get("url") for r in httpx.get("results", []) if r.get("url")
        ]

    dalfox = await dispatch_scan_stage("dalfox", {"urls": urls_for_active_scans})
    results["dalfox"] = dalfox

    ffuf = await dispatch_scan_stage("ffuf", {"urls": urls_for_active_scans})
    results["ffuf"] = ffuf

    if include_sqlmap:
        sqlmap_target = next((u for u in urls_for_active_scans if "?" in u), discovered_targets[0])
        sqlmap = await dispatch_scan_stage(
            "sqlmap",
            {
                "target": sqlmap_target,
                "scope_rules": scope_rules,
                "approved_by_human": sqlmap_approved,
                "approval_token": sqlmap_approval_token,
            },
        )
        results["sqlmap"] = sqlmap

    processed = process_scan_results(results)

    return {
        "status": "completed",
        "target": target,
        "workflow": workflow,
        "results": processed,
    }
