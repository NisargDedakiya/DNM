"""
Distributed worker consuming prioritized jobs and executing them safely.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.triage_service import triage_finding
from backend.cluster.worker_registry import WorkerRegistry
from backend.core.events import EventType
from backend.core.redis import get_redis
from backend.core.redis_streams import redis_streams
from backend.exposure.exposure_tracker import ExposureTracker
from backend.health.worker_health import WorkerHealth
from backend.models.cluster_job import ClusterJob
from backend.queues.priority_queue import PriorityQueue
from backend.security.event_isolation import event_guard
from backend.services.event_service import event_service
from backend.services.scope_service import validate_pipeline_targets
from backend.workers.distributed.task_executor import TaskExecutor

logger = logging.getLogger(__name__)


class DistributedWorker:
    """Consumes cluster jobs, validates them, executes tools, and publishes events."""

    def __init__(self, db: AsyncSession, worker_id: UUID, region: str, capabilities: dict[str, Any] | None = None):
        self.db = db
        self.worker_id = worker_id
        self.region = region
        self.capabilities = capabilities or {}
        self.registry = WorkerRegistry(db)
        self.queue = PriorityQueue()
        self.executor = TaskExecutor()
        self.health = WorkerHealth()
        self.exposure_tracker = ExposureTracker(db)
        self._running = False

    async def run(self, organization_id: str, scopes: list[str] | None = None) -> dict[str, Any]:
        self._running = True
        processed = 0
        failures = 0

        await self.registry.register_worker(self.worker_id, self.region, capabilities=self.capabilities, organization_id=organization_id)
        await event_service.emit_event(EventType.CLUSTER_WORKER_REGISTERED, organization_id, {"worker_id": str(self.worker_id), "region": self.region})

        while self._running:
            job = await self.queue.dequeue(organization_id)
            if not job:
                await asyncio.sleep(1)
                continue

            try:
                await self._handle_job(job, organization_id, scopes or [])
                processed += 1
            except Exception as exc:
                failures += 1
                logger.exception("Distributed worker failed job %s: %s", job.get("job_id"), exc)
                await event_service.emit_event(EventType.CLUSTER_JOB_FAILED, organization_id, {"job_id": job.get("job_id"), "error": str(exc)})

        return {"processed": processed, "failures": failures}

    async def stop(self) -> None:
        self._running = False
        await self.registry.deregister_worker(self.worker_id)

    async def _handle_job(self, job: dict[str, Any], organization_id: str, scopes: list[str]) -> dict[str, Any]:
        if not self._is_approved(job):
            await self._mark_job(job, organization_id, "awaiting_approval")
            await event_service.emit_event(EventType.APPROVAL_REQUESTED, organization_id, {"job_id": job.get("job_id"), "task_type": job.get("task_type")})
            return {"status": "awaiting_approval"}

        await self._mark_job(job, organization_id, "running")
        await event_service.emit_event(EventType.CLUSTER_JOB_STARTED, organization_id, {"job_id": job.get("job_id"), "task_type": job.get("task_type")})

        payload = job.get("payload", {})
        targets = payload.get("targets") or ([payload.get("target")] if payload.get("target") else [])
        validated = await validate_pipeline_targets(
            [target for target in targets if target],
            scopes=scopes,
            user_id=str(payload.get("user_id") or payload.get("created_by_id") or "system"),
            program_id=str(payload.get("program_id") or "") or None,
            allowlist=payload.get("allowlist"),
            rate_limit=payload.get("rate_limit"),
            concurrency_limit=payload.get("concurrency_limit"),
        ) if targets else []

        if validated:
            await event_service.emit_event(EventType.SCAN_PROGRESS, organization_id, {"job_id": job.get("job_id"), "validated_targets": len(validated)})

        tool = payload.get("tool") or self._default_tool(job.get("task_type", "subfinder"))
        tool_args = self._build_tool_args(tool, payload, validated)
        result = await self.executor.execute_tool(tool, tool_args)

        await self._stream_result_events(organization_id, job, result)
        await self._publish_findings_and_triage(organization_id, job, result)
        await self._mark_job(job, organization_id, "completed", meta=result)
        await event_service.emit_event(EventType.CLUSTER_JOB_COMPLETED, organization_id, {"job_id": job.get("job_id"), "result": result})
        return result

    def _is_approved(self, job: dict[str, Any]) -> bool:
        payload = job.get("payload", {})
        if payload.get("approval_status") in {"granted", True, "approved"}:
            return True
        if payload.get("approved") is True:
            return True
        return False

    def _default_tool(self, task_type: str) -> str:
        mapping = {
            "recon_scan": "subfinder",
            "subfinder": "subfinder",
            "httpx": "httpx",
            "katana": "katana",
            "nuclei": "nuclei",
            "ffuf": "ffuf",
            "dalfox": "dalfox",
        }
        return mapping.get(task_type, "subfinder")

    def _build_tool_args(self, tool: str, payload: dict[str, Any], validated_targets: list[dict[str, Any]]) -> list[str]:
        targets = [item["host"] if isinstance(item, dict) and item.get("host") else item.get("target") for item in validated_targets]
        targets = [target for target in targets if target]
        if not targets:
            target = payload.get("target") or payload.get("host")
            if target:
                targets = [str(target)]

        if tool == "subfinder":
            return ["-silent", "-d", targets[0]] if targets else ["-silent"]
        if tool == "httpx":
            return ["-silent", "-json", "-u", targets[0]] if targets else ["-silent", "-json"]
        if tool == "katana":
            return ["-silent", "-u", targets[0]] if targets else ["-silent"]
        if tool == "nuclei":
            return ["-silent", "-json", "-u", targets[0]] if targets else ["-silent", "-json"]
        if tool == "ffuf":
            return ["-u", f"{targets[0].rstrip('/')}/FUZZ", "-w", payload.get("wordlist", "wordlists/common.txt"), "-t", "10"] if targets else ["-t", "10"]
        if tool == "dalfox":
            return ["url", targets[0]] if targets else []
        return targets

    async def _stream_result_events(self, organization_id: str, job: dict[str, Any], result: dict[str, Any]) -> None:
        payload = {"job_id": job.get("job_id"), "task_type": job.get("task_type"), "result": result}
        await redis_streams.publish_event("cluster_worker_events", {"org_id": organization_id, "job_id": job.get("job_id"), "payload": payload})
        await event_service.emit_event(EventType.SCAN_PROGRESS, organization_id, payload)

    async def _publish_findings_and_triage(self, organization_id: str, job: dict[str, Any], result: dict[str, Any]) -> None:
        finding_title = f"{job.get('task_type')} result"
        severity = job.get("payload", {}).get("severity") or "medium"
        evidence = result.get("stdout") or result.get("stderr")
        triage = await triage_finding(
            title=finding_title,
            severity=severity,
            description=f"Distributed execution completed for job {job.get('job_id')}",
            endpoint=job.get("payload", {}).get("target") or job.get("payload", {}).get("host"),
            evidence=evidence,
        )
        await event_service.emit_event(
            EventType.FINDING_CREATED,
            organization_id,
            {
                "job_id": job.get("job_id"),
                "title": finding_title,
                "severity": str(triage.severity.value if hasattr(triage.severity, 'value') else triage.severity),
                "confidence": triage.confidence,
            },
        )

    async def _mark_job(self, job: dict[str, Any], organization_id: str, status: str, meta: dict[str, Any] | None = None) -> None:
        cluster_job = await self.db.get(ClusterJob, UUID(job["job_id"]))
        if cluster_job:
            cluster_job.status = status
            if status == "running":
                from datetime import datetime, timezone

                cluster_job.started_at = datetime.now(timezone.utc)
            if status in {"completed", "failed"}:
                from datetime import datetime, timezone

                cluster_job.completed_at = datetime.now(timezone.utc)
            if meta is not None:
                cluster_job.payload = {**(cluster_job.payload or {}), "result": meta}
            await self.db.flush()

