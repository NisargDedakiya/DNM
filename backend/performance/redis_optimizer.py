"""
Redis stream and queue pressure helpers.
"""
from __future__ import annotations

from typing import Any


def optimize_streams(streams: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(streams, list):
        stream_map = {str(item.get("stream") or item.get("name") or f"stream_{index}"): item for index, item in enumerate(streams)}
    else:
        stream_map = dict(streams)

    trimmed = {
        name: {
            "depth": int(data.get("depth", 0)) if isinstance(data, dict) else 0,
            "consumer_groups": int(data.get("consumer_groups", 0)) if isinstance(data, dict) else 0,
            "recommendation": "trim" if (data.get("depth", 0) if isinstance(data, dict) else 0) > 1000 else "steady",
        }
        for name, data in stream_map.items()
    }
    return {
        "streams": trimmed,
        "maxlen": 5000,
        "trim_policy": "approximate",
        "batch_read_size": 100,
        "consumer_group_prefetch": 50,
    }


def monitor_queue_depth(queue_depths: dict[str, int]) -> dict[str, Any]:
    normalized = {name: max(0, int(depth)) for name, depth in queue_depths.items()}
    total_depth = sum(normalized.values())
    hot_queues = sorted(normalized.items(), key=lambda item: item[1], reverse=True)
    backlog_pressure = min(1.0, total_depth / 5000.0)
    return {
        "total_depth": total_depth,
        "backlog_pressure": round(backlog_pressure, 3),
        "hot_queues": [{"queue": name, "depth": depth} for name, depth in hot_queues[:5]],
        "healthy": backlog_pressure < 0.7,
        "recommended_action": "scale_workers" if backlog_pressure >= 0.7 else "steady_state",
    }


def reduce_event_pressure(events: list[dict[str, Any]], max_events: int = 500) -> dict[str, Any]:
    retained: list[dict[str, Any]] = []
    dropped = 0
    for event in events:
        if len(retained) >= max_events:
            dropped += 1
            continue
        if str(event.get("event") or event.get("type") or "") in {"heartbeat", "typing", "cursor_move"}:
            dropped += 1
            continue
        retained.append(event)
    pressure = len(events) / max(1, max_events)
    return {
        "retained": retained,
        "retained_count": len(retained),
        "dropped_count": dropped,
        "pressure_ratio": round(pressure, 3),
        "should_throttle": pressure > 1.0,
    }
