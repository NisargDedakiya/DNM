"""
Plugin lifecycle orchestration with sandboxed hook execution.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from backend.plugins.plugin_sandbox import create_plugin_sandbox, enforce_plugin_permissions, monitor_plugin_execution

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PluginRuntime:
    organization_id: UUID
    plugin_id: UUID
    name: str
    version: str
    manifest: dict[str, Any]
    sandbox: dict[str, Any]
    hooks: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = field(default_factory=dict)
    active: bool = True
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PluginEngine:
    def __init__(self):
        self._runtimes: dict[str, PluginRuntime] = {}

    def _key(self, organization_id: UUID, plugin_id: UUID) -> str:
        return f"{organization_id}:{plugin_id}"

    async def register_plugin(
        self,
        organization_id: UUID,
        plugin_id: UUID,
        name: str,
        version: str,
        manifest: dict[str, Any],
        hooks: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        sandbox = create_plugin_sandbox(
            organization_id=organization_id,
            plugin_name=name,
            permissions=[str(permission) for permission in manifest.get("permissions", [])],
        )
        runtime = PluginRuntime(
            organization_id=organization_id,
            plugin_id=plugin_id,
            name=name,
            version=version,
            manifest=manifest,
            sandbox=sandbox,
            hooks=hooks or {},
        )
        self._runtimes[self._key(organization_id, plugin_id)] = runtime
        return {
            "plugin_id": str(plugin_id),
            "organization_id": str(organization_id),
            "name": name,
            "version": version,
            "sandbox": sandbox,
            "hook_count": len(runtime.hooks),
            "active": runtime.active,
        }

    async def execute_plugin_hook(
        self,
        organization_id: UUID,
        plugin_id: UUID,
        hook_name: str,
        payload: dict[str, Any],
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        runtime = self._runtimes.get(self._key(organization_id, plugin_id))
        if not runtime or not runtime.active:
            return {"status": "unavailable", "organization_id": str(organization_id), "plugin_id": str(plugin_id)}

        permission_check = enforce_plugin_permissions(runtime.sandbox, list(runtime.manifest.get("permissions", [])))
        if not permission_check["permission_check_passed"]:
            return {
                "status": "blocked",
                "reason": "permission_denied",
                "granted_permissions": permission_check["granted_permissions"],
                "denied_permissions": permission_check["denied_permissions"],
            }

        hook = runtime.hooks.get(hook_name)
        execution_result: dict[str, Any]
        if hook is None:
            execution_result = {
                "status": "noop",
                "hook": hook_name,
                "payload": payload,
            }
        else:
            try:
                execution_result = hook(payload)
                if not isinstance(execution_result, dict):
                    execution_result = {"status": "ok", "result": execution_result}
            except Exception as exc:  # pragma: no cover - runtime safety
                logger.warning("Plugin hook failed: %s", exc)
                execution_result = {"status": "error", "error": str(exc)}

        telemetry = monitor_plugin_execution(runtime.sandbox, metrics)
        return {
            "status": execution_result.get("status", "ok"),
            "organization_id": str(organization_id),
            "plugin_id": str(plugin_id),
            "hook": hook_name,
            "execution": execution_result,
            "telemetry": telemetry,
        }

    async def unload_plugin(self, organization_id: UUID, plugin_id: UUID) -> dict[str, Any]:
        runtime = self._runtimes.pop(self._key(organization_id, plugin_id), None)
        if not runtime:
            return {"status": "not_loaded", "organization_id": str(organization_id), "plugin_id": str(plugin_id)}
        runtime.active = False
        return {
            "status": "unloaded",
            "organization_id": str(organization_id),
            "plugin_id": str(plugin_id),
            "plugin_name": runtime.name,
        }


plugin_engine = PluginEngine()
