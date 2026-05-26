"""
WebSocket throughput helpers for batching and noise reduction.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


_NOISY_EVENTS = {"heartbeat", "typing", "cursor_move", "progress_ping"}
_HIGH_PRIORITY_EVENTS = {"alert", "p1", "finding.created", "scan.completed", "scan.failed", "realtime.notification"}


def batch_events(events: list[dict[str, Any]], batch_size: int = 25) -> list[list[dict[str, Any]]]:
    ordered = reduce_realtime_noise(events)
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    for event in ordered:
        current_batch.append(event)
        if len(current_batch) >= max(1, int(batch_size)):
            batches.append(current_batch)
            current_batch = []
    if current_batch:
        batches.append(current_batch)
    return batches


def optimize_event_delivery(events: list[dict[str, Any]], batch_size: int = 25) -> dict[str, Any]:
    reduced = reduce_realtime_noise(events)
    batched = batch_events(reduced, batch_size=batch_size)
    priority_events = [event for event in reduced if _event_name(event) in _HIGH_PRIORITY_EVENTS]
    return {
        "original_event_count": len(events),
        "delivered_event_count": len(reduced),
        "dropped_noise_count": len(events) - len(reduced),
        "batch_count": len(batched),
        "batches": batched,
        "priority_events": priority_events,
        "delivery_mode": "batched",
    }


def reduce_realtime_noise(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reduced: list[dict[str, Any]] = []
    last_signature: tuple[str, str, str | None] | None = None
    for event in events:
        name = _event_name(event)
        if name in _NOISY_EVENTS:
            continue
        signature = (str(event.get("organization_id") or ""), name, str(event.get("entity_id") or event.get("id") or event.get("resource_id") or ""))
        if signature == last_signature:
            continue
        reduced.append(event)
        last_signature = signature
    return reduced


def _event_name(event: dict[str, Any]) -> str:
    return str(event.get("event") or event.get("type") or event.get("name") or "event")
