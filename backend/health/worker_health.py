"""
Worker heartbeat and health evaluation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.models.worker_node import WorkerNode

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None


class WorkerHealth:
    """Health calculations for worker nodes."""

    async def check_worker_health(self, worker: WorkerNode) -> dict[str, Any]:
        cpu = float(psutil.cpu_percent(interval=0.0)) if psutil else 0.0
        memory = float(psutil.virtual_memory().percent) if psutil else 0.0
        health_score = self.calculate_health_score(worker, cpu, memory)
        return {
            "worker_id": str(worker.id),
            "cpu_percent": cpu,
            "memory_percent": memory,
            "health_score": health_score,
            "failure": self.detect_worker_failure(worker, health_score),
            "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
        }

    def calculate_health_score(self, worker: WorkerNode, cpu_percent: float = 0.0, memory_percent: float = 0.0) -> float:
        heartbeat_age = 0.0
        if worker.last_heartbeat:
            heartbeat_age = max(0.0, (datetime.now(timezone.utc) - worker.last_heartbeat).total_seconds())
        heartbeat_penalty = min(1.0, heartbeat_age / 300.0)
        load_penalty = min(1.0, (worker.current_load or 0) / 10.0)
        resource_penalty = min(1.0, ((cpu_percent / 100.0) + (memory_percent / 100.0)) / 2.0)
        score = 1.0 - (heartbeat_penalty * 0.45 + load_penalty * 0.35 + resource_penalty * 0.2)
        return round(max(0.0, min(1.0, score)), 3)

    def detect_worker_failure(self, worker: WorkerNode, health_score: float | None = None) -> bool:
        score = health_score if health_score is not None else self.calculate_health_score(worker)
        stale = False
        if worker.last_heartbeat:
            stale = (datetime.now(timezone.utc) - worker.last_heartbeat).total_seconds() > 600
        return stale or score < 0.35 or (worker.status or "").lower() == "offline"

