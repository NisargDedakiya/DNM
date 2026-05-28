"""
Disaster recovery orchestration helpers.
"""
from __future__ import annotations

from typing import Any

from backend.recovery.backup_manager import create_backup_snapshot, restore_backup, rotate_old_snapshots


def initiate_recovery(organization_id: str, incident: dict[str, Any]) -> dict[str, Any]:
    """Kick off an org-scoped recovery workflow."""
    snapshot = create_backup_snapshot(organization_id, snapshot_type=incident.get("snapshot_type", "full"))
    return {
        "organization_id": organization_id,
        "incident": incident,
        "snapshot": snapshot,
        "recovery_stage": "initiated",
        "status": "in_progress",
    }


def restore_cluster_state(organization_id: str, snapshot_id: str) -> dict[str, Any]:
    """Restore cluster state from a backup snapshot."""
    restored = restore_backup(snapshot_id, organization_id)
    return {
        "organization_id": organization_id,
        "snapshot_id": snapshot_id,
        "restoration": restored,
        "status": restored["status"],
    }


def validate_recovery_integrity(recovery_state: dict[str, Any]) -> dict[str, Any]:
    """Validate that the recovery workflow is internally consistent."""
    has_snapshot = bool(recovery_state.get("snapshot") or recovery_state.get("snapshot_id"))
    status = "valid" if has_snapshot else "invalid"
    return {
        "valid": has_snapshot,
        "status": status,
        "summary": "Recovery state validated" if has_snapshot else "Recovery state incomplete",
    }

async def cleanup_orphan_jobs(db: AsyncSession) -> int:
    """
    Scans for running jobs whose worker went offline or that timed out,
    and transitions them back to queued status (or fails them if max retries reached).
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from backend.models.cluster_job import ClusterJob
    from backend.models.worker_node import WorkerNode
    from backend.queues.priority_queue import PriorityQueue
    from backend.core.redis import get_redis
    import json
    import time
    import logging

    logger = logging.getLogger(__name__)
    
    # Thresholds: worker heartbeat timeout = 2 mins, execution timeout = 30 mins
    heartbeat_timeout = datetime.now(timezone.utc) - timedelta(minutes=2)
    execution_timeout = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    stmt = select(ClusterJob).where(ClusterJob.status == "running")
    result = await db.execute(stmt)
    running_jobs = result.scalars().all()
    
    recovered_count = 0
    priority_queue = PriorityQueue()
    
    for job in running_jobs:
        should_recover = False
        reason = ""
        
        # Check execution timeout
        if job.started_at and job.started_at.replace(tzinfo=timezone.utc) < execution_timeout:
            should_recover = True
            reason = "execution_timeout"
        else:
            # Check assigned worker status
            if job.assigned_worker:
                worker = await db.get(WorkerNode, job.assigned_worker)
                if not worker or not worker.last_heartbeat or worker.last_heartbeat.replace(tzinfo=timezone.utc) < heartbeat_timeout or worker.status == "offline":
                    should_recover = True
                    reason = "worker_offline"
        
        if should_recover:
            logger.warning(f"Orphan job detected: {job.id} (reason: {reason}). Recovering...")
            job.attempts = int(job.attempts or 0) + 1
            MAX_RETRIES = 3
            
            if job.attempts < MAX_RETRIES:
                job.status = "queued"
                job.assigned_worker = None
                job.started_at = None
                await db.flush()
                
                queue_payload = {
                    "job_id": str(job.id),
                    "organization_id": str(job.organization_id),
                    "task_type": job.task_type,
                    "payload": job.payload or {},
                    "priority": job.priority,
                    "attempts": job.attempts,
                }
                await priority_queue.enqueue(str(job.organization_id), queue_payload, priority=job.priority)
                logger.info(f"Re-enqueued orphan job {job.id} (attempt {job.attempts}/{MAX_RETRIES}).")
            else:
                job.status = "failed"
                job.failure_reason = f"Orphan cleanup: execution failed (reason: {reason}) after {MAX_RETRIES} attempts."
                job.assigned_worker = None
                await db.flush()
                
                # Route to DLQ list in Redis
                redis_client = await get_redis()
                dlq_payload = {
                    "job_id": str(job.id),
                    "organization_id": str(job.organization_id),
                    "task_type": job.task_type,
                    "payload": job.payload or {},
                    "error": job.failure_reason,
                    "failed_at": time.time(),
                    "attempts": job.attempts
                }
                await redis_client.lpush("cluster_jobs:dlq", json.dumps(dlq_payload))
                logger.error(f"Orphan job {job.id} reached max retries. Routed to DLQ.")
            
            recovered_count += 1
            
    if recovered_count > 0:
        await db.commit()
        
    return recovered_count