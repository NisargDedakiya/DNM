"""
Marketplace orchestration service for plugins and enterprise integrations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.connectors.jira_connector import create_ticket, synchronize_workflow as sync_jira_workflow
from backend.connectors.siem_connector import export_security_event, forward_realtime_alert, synchronize_findings
from backend.connectors.slack_connector import notify_investigation, request_approval, send_alert
from backend.connectors.soar_connector import create_incident, orchestrate_response, trigger_playbook
from backend.core.permissions import Permission, RBACService
from backend.marketplace.plugin_validator import validate_plugin_security
from backend.marketplace.registry import MarketplaceRegistry
from backend.models.integration_connector import IntegrationConnector
from backend.models.plugin import Plugin
from backend.models.plugin_installation import PluginInstallation
from backend.models.user import User
from backend.plugins.plugin_engine import plugin_engine
from backend.plugins.plugin_loader import load_plugin


class MarketplaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = MarketplaceRegistry(db)

    async def _require_access(self, user: User, organization_id: UUID, write: bool = False) -> None:
        rbac = RBACService(self.db)
        await rbac.validate_workspace_access(user.id, organization_id)
        permission = Permission.MANAGE_ORG if write else Permission.VIEW_ASSETS
        await rbac.check_permission(user.id, organization_id, permission)

    async def install_plugin(
        self,
        organization_id: UUID,
        user_id: UUID,
        plugin_source: dict[str, Any],
    ) -> dict[str, Any]:
        result = load_plugin(plugin_source)
        security = validate_plugin_security(result["manifest"])
        if not security["approved"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plugin failed security validation")

        plugin = Plugin(
            organization_id=organization_id,
            name=result["manifest"]["name"],
            version=result["manifest"]["version"],
            permissions=result["manifest"].get("permissions", []),
        )
        self.db.add(plugin)
        await self.db.flush()

        installation = PluginInstallation(
            organization_id=organization_id,
            plugin_id=plugin.id,
            installed_by=user_id,
            installed_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(installation)
        await self.db.commit()
        await self.db.refresh(plugin)
        await self.db.refresh(installation)

        await plugin_engine.register_plugin(
            organization_id=organization_id,
            plugin_id=plugin.id,
            name=plugin.name,
            version=plugin.version,
            manifest=result["manifest"],
        )

        return {
            "plugin": {
                "id": plugin.id,
                "organization_id": plugin.organization_id,
                "name": plugin.name,
                "version": plugin.version,
                "permissions": plugin.permissions or [],
                "created_at": plugin.created_at,
            },
            "installation": {
                "id": installation.id,
                "installed_by": installation.installed_by,
                "installed_at": installation.installed_at,
            },
            "security": security,
        }

    async def execute_marketplace_workflow(
        self,
        organization_id: UUID,
        workflow: dict[str, Any],
    ) -> dict[str, Any]:
        plugin_id = workflow.get("plugin_id")
        hook_name = workflow.get("hook_name") or "workflow.triggered"
        event_payload = workflow.get("payload") or {}
        metrics = workflow.get("metrics") or {}

        plugin_result = await plugin_engine.execute_plugin_hook(
            organization_id=organization_id,
            plugin_id=UUID(str(plugin_id)) if plugin_id else UUID(int=0),
            hook_name=hook_name,
            payload=event_payload,
            metrics=metrics,
        ) if plugin_id else {"status": "skipped", "reason": "missing_plugin_id"}

        connector_events = {
            "siem": export_security_event("siem", workflow.get("siem_event") or event_payload),
            "soar": trigger_playbook("soar", workflow.get("playbook") or "default", workflow),
            "slack": send_alert("slack", workflow.get("slack_alert") or event_payload),
            "jira": create_ticket("SEC", workflow.get("jira_issue") or event_payload),
        }

        if workflow.get("create_incident"):
            connector_events["incident"] = create_incident("soar", workflow.get("incident_title") or "Marketplace Workflow", workflow)
        if workflow.get("request_approval"):
            connector_events["approval"] = request_approval("slack", workflow)
        if workflow.get("sync_workflow"):
            connector_events["workflow_sync"] = sync_jira_workflow("SEC", workflow)
        if workflow.get("notify_investigation"):
            connector_events["investigation"] = notify_investigation("slack", workflow)
        if workflow.get("forward_alert"):
            connector_events["realtime"] = forward_realtime_alert("siem", event_payload)
        if workflow.get("sync_findings"):
            connector_events["findings"] = synchronize_findings("siem", workflow.get("findings") or [])
        if workflow.get("orchestrate_response"):
            connector_events["response"] = orchestrate_response("soar", workflow.get("response_steps") or [])

        return {
            "organization_id": str(organization_id),
            "plugin_result": plugin_result,
            "connector_events": connector_events,
            "requires_human_approval": True,
        }

    async def generate_marketplace_summary(self, organization_id: UUID) -> dict[str, Any]:
        plugin_count = await self.db.scalar(select(func.count(Plugin.id)).where(Plugin.organization_id == organization_id))
        install_count = await self.db.scalar(select(func.count(PluginInstallation.id)).where(PluginInstallation.organization_id == organization_id))
        connector_count = await self.db.scalar(select(func.count(IntegrationConnector.id)).where(IntegrationConnector.organization_id == organization_id))

        plugins = await self.registry.search_marketplace(organization_id)
        connectors_result = await self.db.execute(
            select(IntegrationConnector).where(IntegrationConnector.organization_id == organization_id).order_by(IntegrationConnector.created_at.desc()),
        )
        connectors = connectors_result.scalars().all()

        return {
            "organization_id": str(organization_id),
            "plugins": plugins,
            "plugins_count": int(plugin_count or 0),
            "installations_count": int(install_count or 0),
            "connectors_count": int(connector_count or 0),
            "connectors": [
                {
                    "id": connector.id,
                    "connector_type": connector.connector_type,
                    "configuration": connector.configuration or {},
                    "enabled": connector.enabled,
                    "created_at": connector.created_at,
                }
                for connector in connectors
            ],
            "advisory_note": "Marketplace assets are org-scoped, validated, and sandboxed before use.",
        }

    async def list_connectors(self, organization_id: UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(IntegrationConnector).where(IntegrationConnector.organization_id == organization_id).order_by(IntegrationConnector.created_at.desc()),
        )
        connectors = result.scalars().all()
        return {
            "organization_id": str(organization_id),
            "connectors": [
                {
                    "id": connector.id,
                    "connector_type": connector.connector_type,
                    "configuration": connector.configuration or {},
                    "enabled": connector.enabled,
                    "created_at": connector.created_at,
                }
                for connector in connectors
            ],
            "total": len(connectors),
        }
