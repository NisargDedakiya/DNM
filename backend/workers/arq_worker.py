"""
ARQ worker configuration and entrypoint.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from arq import Worker, create_pool

from backend.core.config import settings
from backend.workers import tasks


@dataclass
class WorkerSettings:
    redis_settings: str = settings.redis_url
    functions: List = [
        tasks.run_recon_pipeline_task,
        tasks.run_nuclei_scan_task,
        tasks.run_katana_scan_task,
        tasks.process_findings_task,
    ]
    max_jobs: int = int(os.getenv("ARQ_MAX_JOBS", "5"))
    burst: bool = False


async def run_worker():
    pool = await create_pool(WorkerSettings.redis_settings)
    try:
        worker = Worker(functions=WorkerSettings.functions, redis_pool=pool, max_jobs=WorkerSettings.max_jobs)
        await worker.async_run()
    finally:
        await pool.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_worker())
