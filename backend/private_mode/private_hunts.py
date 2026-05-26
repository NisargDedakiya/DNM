"""
Private hunt execution and visibility controls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


_PRIVATE_HUNTS: dict[str, dict[str, Any]] = {}


def create_private_hunt(organization_id: str, workspace_id: str, scope: dict[str, Any], created_by: str) -> dict[str, Any]:
    hunt_id = str(uuid4())
    hunt = {
        "id": hunt_id,
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "scope": scope,
        "created_by": created_by,
        "visibility": "private",
        "execution_mode": "isolated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _PRIVATE_HUNTS[hunt_id] = hunt
    return hunt


def restrict_hunt_access(hunt_id: str) -> dict[str, Any]:
    hunt = _PRIVATE_HUNTS.get(hunt_id)
    if not hunt:
        return {"restricted": False, "reason": "hunt_not_found"}
    hunt["visibility"] = "restricted"
    return {
        "restricted": True,
        "hunt_id": hunt_id,
        "organization_id": hunt["organization_id"],
        "workspace_id": hunt["workspace_id"],
    }


def isolate_hunt_execution(hunt_id: str) -> dict[str, Any]:
    hunt = _PRIVATE_HUNTS.get(hunt_id)
    if not hunt:
        return {"isolated": False, "reason": "hunt_not_found"}
    return {
        "isolated": True,
        "hunt_id": hunt_id,
        "event_stream": f"private-hunt:{hunt['organization_id']}:{hunt['workspace_id']}:{hunt_id}",
        "websocket_channel": f"ws:private-hunt:{hunt['organization_id']}:{hunt_id}",
    }
