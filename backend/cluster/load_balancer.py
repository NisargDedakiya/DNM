"""
Worker load balancing helpers for the cluster.
"""
from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from backend.models.worker_node import WorkerNode


class LoadBalancer:
    """Selects workers according to load, health, and capability fit."""

    def calculate_worker_load(self, worker: WorkerNode) -> float:
        health = float(worker.health_score or 0.0)
        load_penalty = float(worker.current_load or 0) / 10.0
        return max(0.0, min(1.0, health - load_penalty))

    def select_worker(
        self,
        workers: list[WorkerNode],
        required_capabilities: list[str] | None = None,
    ) -> WorkerNode | None:
        required_capabilities = [cap.lower() for cap in (required_capabilities or [])]

        candidates: list[WorkerNode] = []
        for worker in workers:
            capabilities = worker.capabilities or {}
            supported = {str(key).lower() for key in capabilities.keys()}
            if required_capabilities and not set(required_capabilities).issubset(supported):
                continue
            candidates.append(worker)

        if not candidates:
            return None

        def heartbeat_timestamp(worker: WorkerNode) -> float:
            if not worker.last_heartbeat:
                return 0.0
            if isinstance(worker.last_heartbeat, datetime):
                return worker.last_heartbeat.replace(tzinfo=worker.last_heartbeat.tzinfo or timezone.utc).timestamp()
            return 0.0

        return sorted(
            candidates,
            key=lambda worker: (
                -self.calculate_worker_load(worker),
                worker.current_load,
                -heartbeat_timestamp(worker),
            ),
        )[0]

    def distribute_tasks(self, workers: list[WorkerNode], tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        assignments: list[dict[str, Any]] = []
        if not workers:
            return assignments

        sorted_workers = sorted(workers, key=lambda worker: (worker.current_load, -(worker.health_score or 0.0)))
        index = 0
        for task in tasks:
            worker = sorted_workers[index % len(sorted_workers)]
            assignments.append({"worker_id": str(worker.id), "task": task})
            index += 1
        return assignments

