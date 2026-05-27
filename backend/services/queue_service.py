"""
Queue service to enqueue background scan jobs using ARQ.
"""
from __future__ import annotations

from typing import Any, List, Optional
from arq import create_pool

from backend.workers import job_manager
from backend.core.config import settings


async def enqueue_recon_pipeline(initial_targets: List[str], user_id: str, program_id: str, scan_id: Optional[str] = None) -> str:
    job_id = await job_manager.create_job("recon_pipeline", user_id, meta={"targets": initial_targets, "program_id": program_id})
    # enqueue into ARQ
    pool = await create_pool(settings.redis_url)
    try:
        await pool.enqueue_job("run_recon_pipeline_task", job_id, initial_targets, user_id, program_id, scan_id)
    finally:
        await pool.close()
    return job_id


async def enqueue_nuclei_scan(endpoints: List[str], user_id: str, program_id: str, scan_id: Optional[str] = None) -> str:
    job_id = await job_manager.create_job("nuclei_scan", user_id, meta={"endpoints_count": len(endpoints)})
    pool = await create_pool(settings.redis_url)
    try:
        await pool.enqueue_job("run_nuclei_scan_task", job_id, endpoints, user_id, program_id, scan_id)
    finally:
        await pool.close()
    return job_id


async def enqueue_katana_scan(targets: List[str], user_id: str, program_id: str) -> str:
    job_id = await job_manager.create_job("katana_scan", user_id, meta={"targets": targets})
    pool = await create_pool(settings.redis_url)
    try:
        await pool.enqueue_job("run_katana_scan_task", job_id, targets, user_id, program_id)
    finally:
        await pool.close()
    return job_id


async def _enqueue_task(function_name: str, *args: Any) -> None:
    pool = await create_pool(settings.redis_url)
    try:
        await pool.enqueue_job(function_name, *args)
    finally:
        await pool.close()


async def enqueue_full_scan(scan_id: str, program_id: str, org_id: str, targets: List[str], tech_stack: str, scope_json: dict, stealth: bool = False) -> str:
    await _enqueue_task("run_full_scan", scan_id, program_id, org_id, targets, tech_stack, scope_json, stealth)
    return scan_id


async def enqueue_dalfox_scan(scan_id: str, program_id: str, org_id: str, urls: List[str], scope_json: dict) -> str:
    await _enqueue_task("run_dalfox_scan", scan_id, program_id, org_id, urls, scope_json)
    return scan_id


async def enqueue_full_scan_pipeline(
    scan_id: str,
    program_id: str,
    org_id: str,
    targets: List[str],
    tech_stack: str,
    scope_json: dict,
    stealth: bool = False,
    created_by_id: Optional[str] = None,
) -> str:
    """
    Enqueue a full scanner pipeline (nuclei → dalfox → chain detection) via ARQ.
    Mirrors enqueue_full_scan but uses the ``full_scan_pipeline`` task name and
    forwards the optional ``created_by_id`` for attribution.

    Returns the scan_id so callers can poll status.
    """
    await _enqueue_task(
        "full_scan_pipeline",
        scan_id,
        program_id,
        org_id,
        targets,
        tech_stack,
        scope_json,
        stealth,
        created_by_id,
    )
    return scan_id
