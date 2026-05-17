"""
ARQ task implementations for background scan execution.

Tasks are designed to be idempotent, safe, and report progress via Redis/pubsub.
"""
from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from arq import Retry

from backend.workers import job_manager
from backend.services.recon_pipeline_service import run_full_pipeline
from backend.websocket.pubsub import publish_event
from backend.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_recon_pipeline_task(ctx, job_id: str, initial_targets: List[str], user_id: str, program_id: str, scan_id: str | None = None):
    """ARQ task wrapper around the recon pipeline.

    ctx is provided by ARQ. This function updates job status and publishes websocket events.
    """
    await job_manager.update_job_status(job_id, "started")
    await publish_event(user_id, {"event": "job_started", "payload": {"job_id": job_id}})

    # create a DB session for pipeline
    async with AsyncSessionLocal() as db:
        try:
            # check cancellation before start
            if await job_manager.is_cancelled(job_id):
                await job_manager.update_job_status(job_id, "cancelled")
                await publish_event(user_id, {"event": "job_cancelled", "payload": {"job_id": job_id}})
                return {"cancelled": True}

            await publish_event(user_id, {"event": "scan_progress", "payload": {"stage": "probe"}})
            summary = await run_full_pipeline(initial_targets, db, user_id, UUID(program_id), scan_id=UUID(scan_id) if scan_id else None)

            await job_manager.update_job_status(job_id, "completed", meta=summary)
            await publish_event(user_id, {"event": "job_completed", "payload": {"job_id": job_id, "summary": summary}})
            return summary

        except Exception as exc:
            logger.exception("Recon pipeline failed for job %s: %s", job_id, exc)
            await job_manager.update_job_status(job_id, "failed", meta={"error": str(exc)})
            await publish_event(user_id, {"event": "job_failed", "payload": {"job_id": job_id, "error": str(exc)}})
            raise Retry(str(exc))


async def run_nuclei_scan_task(ctx, job_id: str, endpoints: List[str], user_id: str, program_id: str, scan_id: str | None = None):
    # wrapper to run nuclei stage only
    await job_manager.update_job_status(job_id, "started")
    await publish_event(user_id, {"event": "nuclei_started", "payload": {"job_id": job_id}})
    async with AsyncSessionLocal() as db:
        try:
            findings = await run_full_pipeline([], db, user_id, UUID(program_id), scan_id=UUID(scan_id) if scan_id else None)
            await job_manager.update_job_status(job_id, "completed", meta={"findings": len(findings)})
            await publish_event(user_id, {"event": "nuclei_completed", "payload": {"job_id": job_id}})
            return findings
        except Exception as exc:
            logger.exception("Nuclei task failed: %s", exc)
            await job_manager.update_job_status(job_id, "failed", meta={"error": str(exc)})
            await publish_event(user_id, {"event": "job_failed", "payload": {"job_id": job_id, "error": str(exc)}})
            raise Retry(str(exc))


async def run_katana_scan_task(ctx, job_id: str, targets: List[str], user_id: str, program_id: str):
    await job_manager.update_job_status(job_id, "started")
    await publish_event(user_id, {"event": "katana_started", "payload": {"job_id": job_id}})
    # Simple: call run_katana_stage from recon service
    from backend.services.recon_pipeline_service import run_katana_stage

    try:
        endpoints = await run_katana_stage(targets, user_id=user_id, program_id=UUID(program_id))
        await job_manager.update_job_status(job_id, "completed", meta={"endpoints": len(endpoints)})
        await publish_event(user_id, {"event": "katana_completed", "payload": {"job_id": job_id, "count": len(endpoints)}})
        return endpoints
    except Exception as exc:
        logger.exception("Katana task failed: %s", exc)
        await job_manager.update_job_status(job_id, "failed", meta={"error": str(exc)})
        await publish_event(user_id, {"event": "job_failed", "payload": {"job_id": job_id, "error": str(exc)}})
        raise Retry(str(exc))


async def process_findings_task(ctx, job_id: str, raw_findings: List[dict], user_id: str, program_id: str, scan_id: str | None = None):
    await job_manager.update_job_status(job_id, "started")
    await publish_event(user_id, {"event": "process_findings_started", "payload": {"job_id": job_id}})
    async with AsyncSessionLocal() as db:
        try:
            from backend.services.recon_pipeline_service import process_findings

            created = await process_findings(raw_findings, db, user_id, UUID(program_id), scan_id=UUID(scan_id) if scan_id else None)
            await db.commit()
            await job_manager.update_job_status(job_id, "completed", meta={"created": len(created)})
            await publish_event(user_id, {"event": "findings_created", "payload": {"job_id": job_id, "count": len(created)}})
            return created
        except Exception as exc:
            logger.exception("Process findings task failed: %s", exc)
            await job_manager.update_job_status(job_id, "failed", meta={"error": str(exc)})
            await publish_event(user_id, {"event": "job_failed", "payload": {"job_id": job_id, "error": str(exc)}})
            raise Retry(str(exc))
