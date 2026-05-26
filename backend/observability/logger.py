"""
Structured JSON logging helpers for telemetry-aware observability.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.observability.tracing import current_trace_context


_SENSITIVE_KEYS = {"token", "access_token", "refresh_token", "authorization", "password", "secret", "api_key", "cookie"}


def _sanitize_fields(data: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        if str(key).lower() in _SENSITIVE_KEYS:
            continue
        if isinstance(value, dict):
            sanitized[key] = _sanitize_fields(value)
        elif isinstance(value, list):
            sanitized[key] = [item for item in value]
        else:
            sanitized[key] = value
    return sanitized


class JSONLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        trace = current_trace_context() or {}
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None) or trace.get("trace_id"),
            "span_id": getattr(record, "span_id", None) or trace.get("span_id"),
            "organization_id": getattr(record, "organization_id", None) or trace.get("organization_id"),
            "flow": getattr(record, "flow", None) or trace.get("flow"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            payload.update(_sanitize_fields(extra_fields))
        return json.dumps(_sanitize_fields(payload), default=str)


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        trace = current_trace_context() or {}
        record.trace_id = getattr(record, "trace_id", None) or trace.get("trace_id")
        record.span_id = getattr(record, "span_id", None) or trace.get("span_id")
        record.organization_id = getattr(record, "organization_id", None) or trace.get("organization_id")
        record.flow = getattr(record, "flow", None) or trace.get("flow")
        return True


def get_structured_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(isinstance(handler.formatter, JSONLogFormatter) for handler in logger.handlers if handler.formatter):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONLogFormatter())
        logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
    if not any(isinstance(f, TraceContextFilter) for f in logger.filters):
        logger.addFilter(TraceContextFilter())
    return logger


def log_event(logger: logging.Logger, level: str, message: str, **fields: Any) -> None:
    record = logger.makeRecord(logger.name, getattr(logging, level.upper(), logging.INFO), __file__, 0, message, args=(), exc_info=None)
    record.extra_fields = _sanitize_fields(fields)
    logger.handle(record)
