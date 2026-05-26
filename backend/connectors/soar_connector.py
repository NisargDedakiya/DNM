"""
SOAR connector helpers for automated response workflows.
"""
from __future__ import annotations

from typing import Any


def trigger_playbook(system: str, playbook_name: str, context: dict[str, Any]) -> dict[str, Any]:
    return {
        "system": system,
        "playbook": playbook_name,
        "context": {
            "organization_id": str(context.get("organization_id") or ""),
            "severity": str(context.get("severity") or "medium"),
            "target": str(context.get("target") or context.get("asset") or "unknown"),
        },
        "status": "queued",
    }


def create_incident(system: str, title: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "system": system,
        "incident": {
            "title": title,
            "severity": str(details.get("severity") or "medium"),
            "summary": str(details.get("summary") or ""),
        },
        "status": "created",
    }


def orchestrate_response(system: str, response_steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "system": system,
        "steps": [
            {
                "name": str(step.get("name") or step.get("action") or "response_step"),
                "priority": int(step.get("priority") or index + 1),
                "status": "ready",
            }
            for index, step in enumerate(response_steps)
        ],
    }
