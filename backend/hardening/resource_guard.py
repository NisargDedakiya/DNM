"""
Resource protection helpers for distributed worker isolation.
"""
from __future__ import annotations

from typing import Any


DEFAULT_BOUNDARIES = {
    "cpu_percent": 70,
    "memory_percent": 75,
    "worker_utilization_percent": 80,
}


def monitor_resource_usage(resource_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Normalize resource metrics for enforcement decisions."""
    cpu = float(resource_snapshot.get("cpu_percent") or 0)
    memory = float(resource_snapshot.get("memory_percent") or 0)
    workers = float(resource_snapshot.get("worker_utilization_percent") or 0)
    pressure = min(1.0, (cpu / 100.0) * 0.4 + (memory / 100.0) * 0.4 + (workers / 100.0) * 0.2)
    return {
        "cpu_percent": cpu,
        "memory_percent": memory,
        "worker_utilization_percent": workers,
        "pressure_score": round(pressure, 3),
    }


def enforce_resource_boundaries(resource_snapshot: dict[str, Any], boundaries: dict[str, Any] | None = None) -> dict[str, Any]:
    """Detect when resource use crosses safe boundaries."""
    monitored = monitor_resource_usage(resource_snapshot)
    boundaries = boundaries or DEFAULT_BOUNDARIES
    violations = [name for name, limit in boundaries.items() if monitored.get(name, 0) > float(limit)]
    return {
        "monitored": monitored,
        "boundaries": boundaries,
        "violations": violations,
        "isolation_required": bool(violations),
        "severity": "critical" if len(violations) >= 2 else "high" if violations else "low",
    }


def isolate_resource_pressure(resource_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Provide a bounded response for pressure isolation."""
    enforcement = enforce_resource_boundaries(resource_snapshot)
    if enforcement["violations"]:
        return {
            **enforcement,
            "action": "rebalance_workers",
            "recommended_steps": ["pause_aggressive_scans", "shed_low_priority_jobs", "move_hot_workloads"],
        }
    return {
        **enforcement,
        "action": "steady_state",
        "recommended_steps": ["continue_monitoring"],
    }