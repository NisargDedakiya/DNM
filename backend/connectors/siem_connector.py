"""
SIEM connector helpers for structured security export.
"""
from __future__ import annotations

from typing import Any


def _sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(event.get("id") or event.get("event_id") or ""),
        "organization_id": str(event.get("organization_id") or event.get("org_id") or ""),
        "type": str(event.get("type") or event.get("event_type") or "unknown"),
        "severity": str(event.get("severity") or "medium"),
        "title": str(event.get("title") or event.get("name") or "security event"),
        "summary": str(event.get("summary") or event.get("message") or ""),
        "created_at": event.get("created_at"),
    }


def export_security_event(system: str, event: dict[str, Any]) -> dict[str, Any]:
    return {
        "system": system,
        "exported_event": _sanitize_event(event),
        "status": "ready",
    }


def forward_realtime_alert(system: str, alert: dict[str, Any]) -> dict[str, Any]:
    return {
        "system": system,
        "alert": _sanitize_event(alert),
        "delivery": "queued",
    }


def synchronize_findings(system: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "system": system,
        "count": len(findings),
        "findings": [_sanitize_event(finding) for finding in findings],
    }
