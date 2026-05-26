"""
WebSocket telemetry helpers for connection health and delivery visibility.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from backend.metrics.prometheus_metrics import prometheus_metrics
from backend.observability.metrics_collector import emit_metric_event, record_metric

_EVENT_DELIVERY: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=500))


async def monitor_connection_health(organization_id: str) -> dict[str, Any]:
    from backend.websocket.manager import websocket_manager

    org_connections = websocket_manager.active_connections.get(str(organization_id), {})
    connection_count = sum(len(connections) for connections in org_connections.values())
    reconnect_count = sum(1 for event in _EVENT_DELIVERY[str(organization_id)] if event.get("event") == "reconnect")
    latency_values = [float(item.get("latency_ms", 0.0)) for item in _EVENT_DELIVERY[str(organization_id)] if item.get("latency_ms") is not None]
    healthy = connection_count > 0 or bool(latency_values)
    summary = {
        "healthy": healthy,
        "connection_count": connection_count,
        "active_users": len(org_connections),
        "reconnects": reconnect_count,
        "avg_delivery_latency_ms": round(mean(latency_values), 3) if latency_values else 0.0,
        "last_event_at": _EVENT_DELIVERY[str(organization_id)][-1]["recorded_at"] if _EVENT_DELIVERY[str(organization_id)] else None,
    }
    await record_metric("websocket.connection_count", connection_count, organization_id=str(organization_id))
    return summary


async def track_event_delivery(organization_id: str, event_type: str, latency_ms: float, delivered: bool = True, trace_id: str | None = None) -> dict[str, Any]:
    payload = {
        "event": event_type,
        "latency_ms": round(float(latency_ms), 3),
        "delivered": bool(delivered),
        "trace_id": trace_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _EVENT_DELIVERY[str(organization_id)].append(payload)
    await emit_metric_event("websocket.delivery_latency_ms", latency_ms, organization_id=str(organization_id), labels={"event_type": event_type, "delivered": delivered})
    await prometheus_metrics.observe_websocket_latency(event_type=event_type, latency_ms=latency_ms, organization_id=organization_id, delivered=delivered)
    return payload


def detect_connection_issues(organization_id: str) -> list[dict[str, Any]]:
    samples = list(_EVENT_DELIVERY[str(organization_id)])
    issues: list[dict[str, Any]] = []
    reconnects = sum(1 for item in samples if item.get("event") == "reconnect")
    if reconnects > 3:
        issues.append({"issue": "reconnect_storm", "severity": "high", "reconnects": reconnects})
    failed_deliveries = sum(1 for item in samples if not item.get("delivered", True))
    if failed_deliveries > 0:
        issues.append({"issue": "delivery_failures", "severity": "medium", "failed_deliveries": failed_deliveries})
    avg_latency = mean([float(item.get("latency_ms", 0.0)) for item in samples]) if samples else 0.0
    if avg_latency > 250:
        issues.append({"issue": "high_latency", "severity": "medium", "avg_latency_ms": round(avg_latency, 3)})
    return issues
