"""
Confidential workspace isolation helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


_STEALTH_WORKSPACES: dict[str, dict[str, Any]] = {}


def create_stealth_workspace(organization_id: str, name: str, created_by: str) -> dict[str, Any]:
    workspace_id = str(uuid4())
    workspace = {
        "id": workspace_id,
        "organization_id": organization_id,
        "name": name,
        "created_by": created_by,
        "stealth_enabled": True,
        "visibility": "restricted",
        "event_stream": f"stealth:{organization_id}:{workspace_id}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _STEALTH_WORKSPACES[workspace_id] = workspace
    return workspace


def isolate_workspace_events(workspace_id: str) -> dict[str, Any]:
    workspace = _STEALTH_WORKSPACES.get(workspace_id)
    if not workspace:
        return {"isolated": False, "reason": "workspace_not_found"}
    return {
        "isolated": True,
        "workspace_id": workspace_id,
        "event_stream": workspace["event_stream"],
        "websocket_channel": f"ws:private:{workspace['organization_id']}:{workspace_id}",
    }


def restrict_workspace_visibility(workspace_id: str) -> dict[str, Any]:
    workspace = _STEALTH_WORKSPACES.get(workspace_id)
    if not workspace:
        return {"restricted": False, "reason": "workspace_not_found"}
    workspace["visibility"] = "hidden"
    return {
        "restricted": True,
        "workspace_id": workspace_id,
        "visibility": workspace["visibility"],
    }
