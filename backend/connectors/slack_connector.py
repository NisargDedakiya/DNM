"""
Slack connector helpers for realtime alerting and approvals.
"""
from __future__ import annotations

from typing import Any


def send_alert(channel: str, alert: dict[str, Any]) -> dict[str, Any]:
    return {
        "channel": channel,
        "message": {
            "title": str(alert.get("title") or "Security Alert"),
            "severity": str(alert.get("severity") or "medium"),
            "summary": str(alert.get("summary") or alert.get("message") or ""),
        },
        "status": "queued",
    }


def notify_investigation(channel: str, investigation: dict[str, Any]) -> dict[str, Any]:
    return {
        "channel": channel,
        "investigation": {
            "id": str(investigation.get("id") or ""),
            "title": str(investigation.get("title") or "Investigation"),
            "status": str(investigation.get("status") or "open"),
        },
        "status": "queued",
    }


def request_approval(channel: str, approval: dict[str, Any]) -> dict[str, Any]:
    return {
        "channel": channel,
        "approval": {
            "id": str(approval.get("id") or ""),
            "subject": str(approval.get("subject") or approval.get("title") or "approval_request"),
            "requested_by": str(approval.get("requested_by") or "system"),
        },
        "status": "pending",
    }
