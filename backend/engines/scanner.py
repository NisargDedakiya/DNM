"""
Advanced scanner orchestrator for high-signal recon pipeline.

Pipeline:
subfinder -> httpx -> fingerprint strategy -> targeted nuclei -> JS/API intelligence
-> katana -> dalfox -> ffuf -> optional sqlmap (approval only)

SCOPE CONTAMINATION FIX (2024):
  Every entry point of run_scan_pipeline now:
  1. Accepts an explicit ``program_id`` parameter so the pipeline is pinned to
     one and only one program.
  2. Explicitly clears the local target list at the start of each run — no
     target from a previous invocation (Bugcrowd, HackerOne, etc.) can bleed
     in through a stale in-process cache.
  3. All discovered sub-targets (from subfinder, httpx, katana) are individually
     re-validated against the program scope before being passed to active tools.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

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
from backend.utils.scope_validator import ScopeValidator

logger = logging.getLogger(__name__)


async def validate_scan_workflow(
    *,
    target: str,
    scope_rules: list[str],
    program_id: str | UUID,
    include_sqlmap: bool,
    sqlmap_approved: bool,
) -> dict[str, Any]:
    """Validate scope and risky workflow approvals before execution.

    Args:
        target:          The primary domain / IP to scan.
        scope_rules:     Flat list of in-scope asset_identifiers for this
                         specific program (already filtered to URL/WILDCARD/CIDR).
        program_id:      The UUID of the program currently being hunted.  This
                         is recorded in every returned dict so downstream callers
                         can always trace back which program owns the check.
        include_sqlmap:  Whether sqlmap is part of the pipeline.
        sqlmap_approved: Whether a human has explicitly approved sqlmap.

    Returns:
        Dict with ``allowed`` (bool), ``reason`` (str), ``scope`` (dict),
        and ``program_id`` (str) keys.
    """
    scope_check = ScopeValidator.check(
        target, {"in_scope": [{"asset_identifier": r} for r in scope_rules]}
    )
    authorized, reason = scope_check

    if not authorized:
        return {
            "allowed": False,
            "reason": "target_out_of_scope",
            "scope": {
                "authorized": False,
                "reason": reason,
                "normalized_target": target,
            },
            "program_id": str(program_id),
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
                "scope": {
                    "authorized": True,
                    "reason": reason,
                    "normalized_target": target,
                },
                "program_id": str(program_id),
                "sqlmap_policy": sqlmap_policy,
            }

    return {
        "allowed": True,
        "reason": "workflow_valid",
        "scope": {
            "authorized": True,
            "reason": reason,
            "normalized_target": target,
        },
        "program_id": str(program_id),
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


def _filter_discovered_targets(
    candidates: list[str],
    scope_rules: list[str],
    program_id: str | UUID,
    stage: str,
) -> list[str]:
    """Re-validate every discovered target against the program scope.

    This is the cross-contamination firewall: even if subfinder or katana
    returns an extra host, it cannot proceed unless it belongs to the
    in-scope list of *this* program.

    Args:
        candidates:  Raw hostnames / URLs discovered by an upstream tool.
        scope_rules: Flat list of in-scope asset_identifiers for the program.
        program_id:  UUID of the program (for logging context only).
        stage:       Name of the tool that produced the candidates (for logging).

    Returns:
        Only the targets that pass the scope check.
    """
    scope_json = {"in_scope": [{"asset_identifier": r} for r in scope_rules]}
    valid: list[str] = []
    for candidate in candidates:
        ok, reason = ScopeValidator.check(candidate, scope_json)
        if ok:
            valid.append(candidate)
        else:
            logger.warning(
                "Scope contamination guard (program=%s, stage=%s): "
                "dropping discovered target %r — %s",
                program_id,
                stage,
                candidate,
                reason,
            )
    return valid


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
    program_id: str | UUID,
    scope_rules: list[str],
    fingerprint_data: list[str] | None = None,
    js_assets: list[dict[str, Any]] | None = None,
    include_sqlmap: bool = False,
    sqlmap_approved: bool = False,
    sqlmap_approval_token: str | None = None,
) -> dict[str, Any]:
    """Run full high-signal recon pipeline with safety controls.

    CONTAMINATION ISOLATION:
    ─────────────────────────
    • ``scope_rules`` MUST be the in-scope asset_identifiers extracted from
      the Program record that matches ``program_id``.  The caller is responsible
      for loading these from the DB before invoking this function.
    • All internal target lists are initialised fresh at the start of this call.
      There are no module-level target caches that could persist between runs.
    • Every host discovered by subfinder / httpx / katana is re-checked against
      ``scope_rules`` before being fed to active scanners (nuclei, dalfox, ffuf).

    Args:
        target:               Primary domain or IP to scan.
        program_id:           UUID of the program being hunted (used for logging
                              and scope isolation tracing).
        scope_rules:          Flat list of in-scope asset_identifiers (already
                              filtered to URL/WILDCARD/CIDR) for ``program_id``.
        fingerprint_data:     Optional tech-stack fingerprint hints.
        js_assets:            Optional pre-collected JS asset list.
        include_sqlmap:       Opt-in to SQLMap (requires human approval).
        sqlmap_approved:      Whether a human has explicitly approved sqlmap.
        sqlmap_approval_token: Optional approval token for sqlmap gate.
    """
    # ── Explicit state reset ─────────────────────────────────────────────────
    # Declared here to make it unambiguous: these are local to this invocation.
    # No cached targets from any prior program (Bugcrowd, HackerOne, etc.) exist
    # in this namespace.
    _local_targets: list[str] = []  # will be populated after subfinder

    # ── Step 0: validate primary target against program scope ────────────────
    workflow = await validate_scan_workflow(
        target=target,
        scope_rules=scope_rules,
        program_id=program_id,
        include_sqlmap=include_sqlmap,
        sqlmap_approved=sqlmap_approved,
    )
    if not workflow["allowed"]:
        logger.warning(
            "Scan pipeline blocked for program=%s target=%r: %s",
            program_id, target, workflow["reason"],
        )
        return {"status": "blocked", "reason": workflow["reason"], "workflow": workflow}

    results: dict[str, Any] = {}

    # ── Step 1: subfinder ────────────────────────────────────────────────────
    subfinder = await dispatch_scan_stage("subfinder", {"target": target})
    results["subfinder"] = subfinder

    # Re-validate every host found by subfinder against the current program scope.
    raw_discovered: list[str] = subfinder.get("results") or []
    _local_targets = _filter_discovered_targets(
        raw_discovered or [workflow["scope"]["normalized_target"]],
        scope_rules,
        program_id,
        "subfinder",
    )
    # Guarantee we have at least the validated primary target.
    if not _local_targets:
        _local_targets = [workflow["scope"]["normalized_target"]]

    # ── Step 2: httpx on first in-scope discovered host ──────────────────────
    httpx_result = await dispatch_scan_stage("httpx", {"target": _local_targets[0]})
    results["httpx"] = httpx_result

    # ── Step 3: fingerprint strategy ─────────────────────────────────────────
    fp_service = FingerprintScanService()
    strategy = fp_service.generate_scan_strategy(
        [
            {
                "target": _local_targets[0],
                "fingerprints": fingerprint_data or [],
                "internet_facing": True,
            }
        ]
    )
    results["fingerprint_strategy"] = strategy

    # ── Step 4: nuclei ───────────────────────────────────────────────────────
    nuclei = await dispatch_scan_stage(
        "nuclei",
        {
            "target": _local_targets[0],
            "fingerprints": fingerprint_data or [],
            "severity": "high",
        },
    )
    results["nuclei"] = nuclei

    # ── Step 5: JS / API surface analysis ────────────────────────────────────
    js_service = JSIntelligenceService()
    js_analysis = js_service.analyze_javascript(js_assets or [])
    results["js_intelligence"] = js_analysis

    api_service = APISurfaceService()
    api_surface = api_service.detect_api_surfaces(js_analysis.get("extracted_endpoints", []))
    api_risk = api_service.analyze_api_risk(api_surface)
    results["api_surface"] = api_surface
    results["api_risk"] = api_risk

    # ── Step 6: katana crawl ─────────────────────────────────────────────────
    katana = await dispatch_scan_stage("katana", {"target": _local_targets[0]})
    results["katana"] = katana

    # Scope-filter all katana-discovered endpoints before feeding to active scanners.
    raw_katana_endpoints: list[str] = katana.get("endpoints", [])
    urls_for_active_scans: list[str] = _filter_discovered_targets(
        raw_katana_endpoints, scope_rules, program_id, "katana"
    )

    if not urls_for_active_scans:
        # Fallback: scope-filter httpx live URLs.
        raw_httpx_urls = [
            r.get("url") for r in httpx_result.get("results", []) if r.get("url")
        ]
        urls_for_active_scans = _filter_discovered_targets(
            raw_httpx_urls, scope_rules, program_id, "httpx-fallback"
        )

    # ── Step 7: dalfox XSS ──────────────────────────────────────────────────
    dalfox = await dispatch_scan_stage("dalfox", {"urls": urls_for_active_scans})
    results["dalfox"] = dalfox

    # ── Step 8: ffuf dir-brute ───────────────────────────────────────────────
    ffuf = await dispatch_scan_stage("ffuf", {"urls": urls_for_active_scans})
    results["ffuf"] = ffuf

    # ── Step 9: optional sqlmap ──────────────────────────────────────────────
    if include_sqlmap:
        # Prefer a parameterised URL; fall back to the first in-scope target.
        sqlmap_target = next(
            (u for u in urls_for_active_scans if "?" in u), _local_targets[0]
        )
        # Final scope check before invoking the most invasive tool.
        scope_json = {"in_scope": [{"asset_identifier": r} for r in scope_rules]}
        sqli_ok, sqli_reason = ScopeValidator.check(sqlmap_target, scope_json)
        if not sqli_ok:
            logger.error(
                "SQLMap target %r failed final scope re-check for program=%s: %s — aborting",
                sqlmap_target, program_id, sqli_reason,
            )
        else:
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
        "program_id": str(program_id),
        "workflow": workflow,
        "results": processed,
    }
