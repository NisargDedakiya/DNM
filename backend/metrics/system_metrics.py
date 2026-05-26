"""
System resource metric collection helpers.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None


def collect_system_metrics() -> dict[str, Any]:
    cpu_percent = float(psutil.cpu_percent(interval=0.0)) if psutil else 0.0
    memory = psutil.virtual_memory() if psutil else None
    disk = psutil.disk_usage(_disk_path()) if psutil else None
    network = psutil.net_io_counters() if psutil else None

    return {
        "cpu_percent": round(cpu_percent, 2),
        "memory_percent": round(float(memory.percent) if memory else 0.0, 2),
        "memory_available_mb": round(float(memory.available) / 1024 / 1024, 2) if memory else 0.0,
        "disk_percent": round(float(disk.percent) if disk else 0.0, 2),
        "disk_free_gb": round(float(disk.free) / 1024 / 1024 / 1024, 2) if disk else 0.0,
        "network_sent_mb": round(float(network.bytes_sent) / 1024 / 1024, 2) if network else 0.0,
        "network_recv_mb": round(float(network.bytes_recv) / 1024 / 1024, 2) if network else 0.0,
        "pressure_score": _pressure_score(cpu_percent, memory.percent if memory else 0.0, disk.percent if disk else 0.0),
    }


def detect_resource_pressure(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if metrics.get("cpu_percent", 0.0) > 85:
        issues.append({"component": "cpu", "issue": "high_cpu", "severity": "high", "value": metrics["cpu_percent"]})
    if metrics.get("memory_percent", 0.0) > 85:
        issues.append({"component": "memory", "issue": "high_memory", "severity": "high", "value": metrics["memory_percent"]})
    if metrics.get("disk_percent", 0.0) > 90:
        issues.append({"component": "disk", "issue": "low_disk_space", "severity": "critical", "value": metrics["disk_percent"]})
    if metrics.get("pressure_score", 0.0) > 0.75:
        issues.append({"component": "system", "issue": "resource_pressure", "severity": "high", "value": metrics["pressure_score"]})
    return issues


def summarize_system_health() -> dict[str, Any]:
    metrics = collect_system_metrics()
    pressure = detect_resource_pressure(metrics)
    health = "degraded" if pressure else "healthy"
    return {
        "status": health,
        "pressure_score": metrics.get("pressure_score", 0.0),
        "issues": pressure,
        "metrics": metrics,
    }


def _pressure_score(cpu_percent: float, memory_percent: float, disk_percent: float) -> float:
    score = ((cpu_percent / 100.0) + (memory_percent / 100.0) + (disk_percent / 100.0)) / 3.0
    return round(max(0.0, min(1.0, score)), 3)


def _disk_path() -> str:
    anchor = Path.cwd().anchor or os.environ.get("SystemDrive", "C:\\")
    return anchor if anchor.endswith(os.sep) else f"{anchor}{os.sep}"
