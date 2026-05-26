"""
Central metrics aggregation for org-scoped telemetry.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from backend.core.events import EventType

_METRICS: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=1000))
_LOCK = asyncio.Lock()

_SENSITIVE_KEYS = {"token", "access_token", "refresh_token", "authorization", "password", "secret", "api_key", "cookie"}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if str(key).lower() not in _SENSITIVE_KEYS}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


async def record_metric(name: str, value: float, organization_id: str | None = None, labels: dict[str, Any] | None = None, trace_id: str | None = None) -> dict[str, Any]:
    metric = {
        "name": name,
        "value": float(value),
        "organization_id": str(organization_id) if organization_id else None,
        "labels": _sanitize(labels or {}),
        "trace_id": trace_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    async with _LOCK:
        _METRICS[name].append(metric)
    return metric


async def aggregate_metrics(organization_id: str | None = None, prefix: str | None = None) -> dict[str, Any]:
    async with _LOCK:
        selected = []
        for metric_name, samples in _METRICS.items():
            if prefix and not metric_name.startswith(prefix):
                continue
            selected.extend(sample for sample in samples if organization_id is None or sample.get("organization_id") == str(organization_id))

    values = [float(item.get("value", 0.0)) for item in selected]
    return {
        "organization_id": str(organization_id) if organization_id else None,
        "prefix": prefix,
        "count": len(selected),
        "min": min(values) if values else 0.0,
        "max": max(values) if values else 0.0,
        "avg": round(mean(values), 3) if values else 0.0,
        "latest": selected[-1] if selected else None,
        "recent_events": selected[-10:],
    }


async def emit_metric_event(name: str, value: float, organization_id: str | None = None, labels: dict[str, Any] | None = None, trace_id: str | None = None) -> dict[str, Any]:
    metric = await record_metric(name, value, organization_id=organization_id, labels=labels, trace_id=trace_id)
    try:
        from backend.services.event_service import event_service

        await event_service.emit_event(EventType.METRIC_RECORDED, str(organization_id) if organization_id else "system", metric)
    except Exception:
        pass
    return metric
