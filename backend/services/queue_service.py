"""
Queue service to enqueue background scan jobs using ARQ.
"""
from __future__ import annotations

from typing import List, Optional
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
