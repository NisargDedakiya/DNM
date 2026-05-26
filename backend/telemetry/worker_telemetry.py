"""
Distributed worker telemetry helpers.
"""
from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any

from backend.health.worker_health import WorkerHealth
from backend.metrics.prometheus_metrics import prometheus_metrics
from backend.observability.metrics_collector import emit_metric_event, record_metric
from backend.models.worker_node import WorkerNode

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None

_worker_health = WorkerHealth()


async def track_worker_load(workers: list[WorkerNode | dict[str, Any]]) -> dict[str, Any]:
    normalized = [_normalize_worker(worker) for worker in workers]
    loads = [float(worker.get("current_load", 0) or 0) for worker in normalized]
    health_scores = [float(worker.get("health_score", 0.0) or 0.0) for worker in normalized]
    summary = {
        "worker_count": len(normalized),
        "busy_workers": sum(1 for worker in normalized if float(worker.get("current_load", 0) or 0) > 0),
        "failed_workers": sum(1 for worker in normalized if str(worker.get("status", "")).lower() == "offline" or float(worker.get("health_score", 0.0) or 0.0) < 0.35),
        "average_load": round(mean(loads), 3) if loads else 0.0,
        "average_health": round(mean(health_scores), 3) if health_scores else 0.0,
        "workers": normalized,
    }
    await record_metric("worker.load.average", summary["average_load"], organization_id=_org_scope(normalized), labels={"kind": "worker"})
    return summary


async def monitor_task_execution(worker_id: str, task_name: str, started_at: datetime, completed_at: datetime, status: str, organization_id: str | None = None) -> dict[str, Any]:
    latency_ms = max(0.0, (completed_at - started_at).total_seconds() * 1000.0)
    payload = {
        "worker_id": str(worker_id),
        "task_name": task_name,
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "recorded_at": completed_at.isoformat(),
    }
    await emit_metric_event("worker.task_latency_ms", latency_ms, organization_id=organization_id, labels={"task_name": task_name, "status": status})
    await prometheus_metrics.observe_worker_task(worker_id=str(worker_id), task_name=task_name, latency_ms=latency_ms, status=status, organization_id=organization_id)
    return payload


def detect_worker_bottlenecks(workers: list[WorkerNode | dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for worker in [_normalize_worker(worker) for worker in workers]:
        if float(worker.get("current_load", 0) or 0) > 10:
            issues.append({"worker_id": worker.get("worker_id"), "issue": "overloaded", "severity": "high", "current_load": worker.get("current_load")})
        if float(worker.get("health_score", 0.0) or 0.0) < 0.4:
            issues.append({"worker_id": worker.get("worker_id"), "issue": "low_health", "severity": "high", "health_score": worker.get("health_score")})
        if worker.get("resource_pressure", 0.0) > 0.8:
            issues.append({"worker_id": worker.get("worker_id"), "issue": "resource_pressure", "severity": "medium", "pressure": worker.get("resource_pressure")})
    return issues


def _normalize_worker(worker: WorkerNode | dict[str, Any]) -> dict[str, Any]:
    if isinstance(worker, WorkerNode):
        health = _worker_health.calculate_health_score(worker)
        return {
            "worker_id": str(worker.id),
            "status": worker.status,
            "current_load": worker.current_load,
            "health_score": worker.health_score if worker.health_score is not None else health,
            "resource_pressure": _resource_pressure(worker),
            "region": worker.region,
            "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
            "organization_id": str(worker.organization_id) if worker.organization_id else None,
        }
    worker_dict = dict(worker)
    worker_dict.setdefault("worker_id", worker_dict.get("id"))
    worker_dict.setdefault("health_score", 0.0)
    worker_dict.setdefault("resource_pressure", 0.0)
    return worker_dict


def _resource_pressure(worker: WorkerNode) -> float:
    cpu = float(psutil.cpu_percent(interval=0.0)) if psutil else 0.0
    memory = float(psutil.virtual_memory().percent) if psutil else 0.0
    return round(min(1.0, ((cpu / 100.0) + (memory / 100.0)) / 2.0), 3)


def _org_scope(workers: list[dict[str, Any]]) -> str | None:
    for worker in workers:
        if worker.get("organization_id"):
            return str(worker.get("organization_id"))
    return None
