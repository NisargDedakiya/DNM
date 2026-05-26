"""
Aggregate cluster health monitoring.
"""
from __future__ import annotations

from statistics import mean
from typing import Any

from backend.health.worker_health import WorkerHealth
from backend.models.worker_node import WorkerNode


class ClusterMonitor:
    """Summarizes cluster-wide health and failure conditions."""

    def __init__(self):
        self.worker_health = WorkerHealth()

    async def monitor_cluster(self, workers: list[WorkerNode]) -> dict[str, Any]:
        worker_metrics = [await self.worker_health.check_worker_health(worker) for worker in workers]
        return {
            "worker_count": len(workers),
            "healthy_workers": sum(1 for metric in worker_metrics if not metric["failure"]),
            "failed_workers": sum(1 for metric in worker_metrics if metric["failure"]),
            "average_health_score": round(mean([metric["health_score"] for metric in worker_metrics]), 3) if worker_metrics else 0.0,
            "workers": worker_metrics,
        }

    def aggregate_cluster_metrics(self, workers: list[WorkerNode]) -> dict[str, Any]:
        if not workers:
            return {"worker_count": 0, "average_load": 0.0, "average_health": 0.0}
        return {
            "worker_count": len(workers),
            "average_load": round(mean([float(worker.current_load or 0) for worker in workers]), 2),
            "average_health": round(mean([float(worker.health_score or 0.0) for worker in workers]), 3),
        }

    def detect_cluster_issues(self, workers: list[WorkerNode]) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for worker in workers:
            if (worker.health_score or 0.0) < 0.35:
                issues.append({"worker_id": str(worker.id), "issue": "low_health", "status": worker.status})
            if (worker.current_load or 0) > 10:
                issues.append({"worker_id": str(worker.id), "issue": "overloaded", "load": worker.current_load})
        return issues

