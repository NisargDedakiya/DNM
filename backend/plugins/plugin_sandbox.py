"""
Isolated sandbox metadata and permission guards for plugins.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class PluginSandbox:
    organization_id: UUID
    plugin_name: str
    allowed_permissions: list[str]
    memory_limit_mb: int = 128
    cpu_limit_pct: int = 25
    network_access: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True


def create_plugin_sandbox(
    organization_id: UUID,
    plugin_name: str,
    permissions: list[str] | None = None,
    memory_limit_mb: int = 128,
    cpu_limit_pct: int = 25,
) -> dict[str, Any]:
    sandbox = PluginSandbox(
        organization_id=organization_id,
        plugin_name=plugin_name,
        allowed_permissions=permissions or [],
        memory_limit_mb=memory_limit_mb,
        cpu_limit_pct=cpu_limit_pct,
    )
    return {
        "organization_id": str(sandbox.organization_id),
        "plugin_name": sandbox.plugin_name,
        "allowed_permissions": sandbox.allowed_permissions,
        "memory_limit_mb": sandbox.memory_limit_mb,
        "cpu_limit_pct": sandbox.cpu_limit_pct,
        "network_access": sandbox.network_access,
        "active": sandbox.active,
        "created_at": sandbox.created_at,
    }


def enforce_plugin_permissions(sandbox: dict[str, Any], requested_permissions: list[str]) -> dict[str, Any]:
    allowed = set(str(permission) for permission in sandbox.get("allowed_permissions", []))
    requested = set(str(permission) for permission in requested_permissions or [])
    granted = sorted(permission for permission in requested if permission in allowed)
    denied = sorted(permission for permission in requested if permission not in allowed)
    return {
        **sandbox,
        "granted_permissions": granted,
        "denied_permissions": denied,
        "permission_check_passed": not denied,
    }


def monitor_plugin_execution(sandbox: dict[str, Any], metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    metrics = metrics or {}
    cpu = float(metrics.get("cpu_pct", 0.0))
    memory = float(metrics.get("memory_mb", 0.0))
    elapsed = float(metrics.get("elapsed_seconds", 0.0))
    return {
        "plugin_name": sandbox.get("plugin_name"),
        "organization_id": sandbox.get("organization_id"),
        "cpu_pct": cpu,
        "memory_mb": memory,
        "elapsed_seconds": elapsed,
        "within_limits": cpu <= float(sandbox.get("cpu_limit_pct", 25)) and memory <= float(sandbox.get("memory_limit_mb", 128)),
        "requires_shutdown": elapsed > 300 or cpu > float(sandbox.get("cpu_limit_pct", 25)) * 1.5,
    }
