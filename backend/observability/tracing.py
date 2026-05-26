"""
Distributed tracing helpers for platform monitoring.
"""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.core.events import EventType

_TRACE_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar("trace_context", default=None)
_SENSITIVE_KEYS = {"token", "access_token", "refresh_token", "authorization", "password", "secret", "api_key", "key", "cookie"}


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_value(item) for key, item in value.items() if str(key).lower() not in _SENSITIVE_KEYS}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item) for item in value)
    return value


def current_trace_context() -> dict[str, Any] | None:
    return _TRACE_CONTEXT.get()


async def start_trace(
    flow: str,
    organization_id: str,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    parent_trace_id: str | None = None,
) -> dict[str, Any]:
    trace_id = str(uuid4())
    span_id = str(uuid4())
    context = {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_trace_id": parent_trace_id,
        "flow": flow,
        "organization_id": str(organization_id),
        "user_id": str(user_id) if user_id else None,
        "metadata": _sanitize_value(metadata or {}),
        "status": "started",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    _TRACE_CONTEXT.set(context)

    try:
        from backend.services.event_service import event_service

        await event_service.emit_event(
            EventType.TRACE_STARTED,
            str(organization_id),
            {"trace_id": trace_id, "span_id": span_id, "flow": flow, "parent_trace_id": parent_trace_id, "metadata": context["metadata"]},
            user_id=user_id,
        )
    except Exception:
        pass

    return context


def attach_trace_context(payload: dict[str, Any], trace_context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = trace_context or current_trace_context() or {}
    safe_payload = _sanitize_value(payload.copy()) if isinstance(payload, dict) else {"value": _sanitize_value(payload)}
    safe_payload["trace_id"] = context.get("trace_id")
    safe_payload["span_id"] = context.get("span_id")
    safe_payload["parent_trace_id"] = context.get("parent_trace_id")
    safe_payload["flow"] = context.get("flow")
    safe_payload["organization_id"] = context.get("organization_id")
    return safe_payload


async def complete_trace(status: str = "completed", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    context = current_trace_context() or {}
    completed = {
        **context,
        "status": status,
        "metadata": _sanitize_value(metadata or {}),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    _TRACE_CONTEXT.set(completed)

    try:
        from backend.services.event_service import event_service

        await event_service.emit_event(
            EventType.TRACE_COMPLETED,
            str(completed.get("organization_id") or "system"),
            {"trace_id": completed.get("trace_id"), "flow": completed.get("flow"), "status": status, "metadata": completed.get("metadata", {})},
            user_id=completed.get("user_id"),
        )
    except Exception:
        pass

    return completed
