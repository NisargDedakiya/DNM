"""
Distributed queue balancing helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def rebalance_queues(queue_state: dict[str, list[dict[str, Any]]] | None) -> dict[str, Any]:
    queue_state = queue_state or {}
    prioritized: dict[str, list[dict[str, Any]]] = {}
    rebalance_plan: list[dict[str, Any]] = []
    for queue_name, tasks in queue_state.items():
        ordered_tasks = prioritize_high_signal_tasks(tasks)
        prioritized[queue_name] = ordered_tasks
        rebalance_plan.append(
            {
                "queue": queue_name,
                "task_count": len(ordered_tasks),
                "high_priority_count": sum(1 for task in ordered_tasks if str(task.get("priority", "medium")).lower() in {"critical", "high"}),
            }
        )
    return {
        "queues": prioritized,
        "rebalance_plan": rebalance_plan,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy": "priority_first",
    }


def prioritize_high_signal_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(tasks, key=_task_score, reverse=True)


def reduce_worker_idle_time(workers: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> dict[str, Any]:
    ordered_workers = sorted(workers, key=lambda worker: float(worker.get("current_load", 0) or 0))
    ordered_tasks = prioritize_high_signal_tasks(tasks)
    assignments: list[dict[str, Any]] = []
    worker_index = 0
    for task in ordered_tasks:
        if not ordered_workers:
            break
        worker = ordered_workers[worker_index % len(ordered_workers)]
        assignments.append(
            {
                "worker_id": worker.get("id") or worker.get("worker_id"),
                "task_id": task.get("id") or task.get("task_id"),
                "priority": task.get("priority", "medium"),
            }
        )
        worker_index += 1
    return {
        "assignments": assignments,
        "idle_worker_count": sum(1 for worker in ordered_workers if float(worker.get("current_load", 0) or 0) == 0),
        "task_count": len(ordered_tasks),
        "worker_count": len(ordered_workers),
    }


def _task_score(task: dict[str, Any]) -> float:
    priority_weight = {
        "critical": 5.0,
        "high": 4.0,
        "medium": 3.0,
        "low": 2.0,
        "info": 1.0,
    }
    priority = str(task.get("priority", "medium")).lower()
    value = float(task.get("signal_strength", task.get("impact_score", 0.0)) or 0.0)
    attempts = float(task.get("attempts", 0) or 0)
    age = float(task.get("age_minutes", 0) or 0)
    return priority_weight.get(priority, 3.0) + value + (age / 100.0) - (attempts * 0.25)
