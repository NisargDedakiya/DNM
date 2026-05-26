"""
Marketplace registry for plugin metadata and version management.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.plugin import Plugin


class MarketplaceRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def publish_plugin(
        self,
        organization_id: UUID,
        name: str,
        version: str,
        permissions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        plugin = Plugin(
            organization_id=organization_id,
            name=name,
            version=version,
            permissions=permissions or [],
        )
        self.db.add(plugin)
        await self.db.commit()
        await self.db.refresh(plugin)
        return {
            "id": plugin.id,
            "organization_id": plugin.organization_id,
            "name": plugin.name,
            "version": plugin.version,
            "permissions": plugin.permissions or [],
            "metadata": metadata or {},
            "published_at": datetime.now(timezone.utc).isoformat(),
        }

    async def search_marketplace(self, organization_id: UUID, query: str | None = None) -> list[dict[str, Any]]:
        stmt = select(Plugin).where(Plugin.organization_id == organization_id).order_by(Plugin.created_at.desc())
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        q = (query or "").lower().strip()
        items = []
        for row in rows:
            if q and q not in row.name.lower() and q not in row.version.lower():
                continue
            items.append({
                "id": row.id,
                "organization_id": row.organization_id,
                "name": row.name,
                "version": row.version,
                "permissions": row.permissions or [],
                "created_at": row.created_at,
            })
        return items

    async def retrieve_plugin_metadata(self, organization_id: UUID, plugin_id: UUID) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(Plugin).where(Plugin.organization_id == organization_id, Plugin.id == plugin_id),
        )
        plugin = result.scalars().first()
        if not plugin:
            return None
        return {
            "id": plugin.id,
            "organization_id": plugin.organization_id,
            "name": plugin.name,
            "version": plugin.version,
            "permissions": plugin.permissions or [],
            "created_at": plugin.created_at,
        }
