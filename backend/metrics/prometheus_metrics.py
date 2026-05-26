"""
Prometheus-compatible metrics exposition helpers.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from statistics import mean
from typing import Any


class PrometheusMetrics:
    def __init__(self) -> None:
        self._samples: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=2000))

    async def observe_scan_latency(self, scan_id: str, latency_ms: float, organization_id: str | None = None, status: str | None = None) -> dict[str, Any]:
        return self._record("scan_latency_ms", latency_ms, organization_id, {"scan_id": scan_id, "status": status})

    async def observe_ai_latency(self, provider: str, model: str, latency_ms: float, organization_id: str | None = None, success: bool = True) -> dict[str, Any]:
        return self._record("ai_latency_ms", latency_ms, organization_id, {"provider": provider, "model": model, "success": success})

    async def observe_websocket_latency(self, event_type: str, latency_ms: float, organization_id: str | None = None, delivered: bool = True) -> dict[str, Any]:
        return self._record("websocket_latency_ms", latency_ms, organization_id, {"event_type": event_type, "delivered": delivered})

    async def observe_worker_load(self, worker_id: str, load: float, organization_id: str | None = None, region: str | None = None) -> dict[str, Any]:
        return self._record("worker_load", load, organization_id, {"worker_id": worker_id, "region": region})

    async def observe_worker_task(self, worker_id: str, task_name: str, latency_ms: float, status: str, organization_id: str | None = None) -> dict[str, Any]:
        return self._record("worker_task_latency_ms", latency_ms, organization_id, {"worker_id": worker_id, "task_name": task_name, "status": status})

    async def set_redis_queue_depth(self, queue_name: str, depth: int, organization_id: str | None = None) -> dict[str, Any]:
        return self._record("redis_queue_depth", depth, organization_id, {"queue_name": queue_name})

    async def observe_finding_throughput(self, organization_id: str, count: int, window_seconds: int = 60) -> dict[str, Any]:
        return self._record("finding_throughput", count, organization_id, {"window_seconds": window_seconds})

    async def render_metrics_text(self, organization_id: str | None = None, summary: dict[str, Any] | None = None) -> str:
        lines = ["# HELP nisarghunter_metric_value Metric sample value", "# TYPE nisarghunter_metric_value gauge"]
        for metric_name, samples in self._samples.items():
            scoped_samples = [sample for sample in samples if organization_id is None or sample.get("organization_id") == str(organization_id)]
            if not scoped_samples:
                continue
            avg_value = mean([float(sample.get("value", 0.0)) for sample in scoped_samples])
            lines.append(f'{metric_name}{{organization_id="{organization_id or "system"}"}} {avg_value}')
        if summary:
            lines.append(f'platform_health_score{{organization_id="{organization_id or "system"}"}} {summary.get("health_score", 0.0)}')
        return "\n".join(lines)

    def _record(self, metric_name: str, value: float, organization_id: str | None, labels: dict[str, Any]) -> dict[str, Any]:
        sample = {
            "metric": metric_name,
            "value": float(value),
            "organization_id": str(organization_id) if organization_id else None,
            "labels": labels,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self._samples[metric_name].append(sample)
        return sample


prometheus_metrics = PrometheusMetrics()
