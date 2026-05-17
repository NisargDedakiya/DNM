"""
Context Service: contextual intelligence aggregation and retrieval.

Provides the service-layer interface for context assembly.  Routes and
higher-level services interact with this class rather than calling
ContextBuilder directly — it adds caching hooks, logging, and error handling.

Security rules
--------------
- All context retrieval is scoped to organization_id.
- Context dicts are safe to return directly to the copilot engine — they
  have already been sanitised by ContextBuilder.
- No context data is cached to Redis (would risk cross-tenant leaks);
  context is always freshly assembled per request.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.context_builder import ContextBuilder
from backend.models.change_event import ChangeEvent
from backend.models.exposure import Exposure
from backend.models.asset import Asset

logger = logging.getLogger(__name__)


class ContextService:
    """
    Context intelligence aggregation service.

    Wraps ContextBuilder with service-level logging and error handling.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._builder = ContextBuilder(db)

    # =========================================================================
    # ASSET CONTEXT
    # =========================================================================

    async def get_asset_context(
        self,
        organization_id: UUID,
        asset_id: UUID,
    ) -> dict[str, Any]:
        """
        Retrieve and assemble full investigation context for an asset.

        Returns a sanitised, token-bounded context dict.
        """
        try:
            ctx = await self._builder.build_asset_context(organization_id, asset_id)
            logger.debug(
                "Asset context assembled: org=%s asset=%s nodes=%d",
                organization_id, asset_id,
                len(ctx.get("related_data", {}).get("endpoints", [])),
            )
            return ctx
        except Exception as exc:
            logger.error("Asset context assembly failed: org=%s asset=%s err=%s",
                         organization_id, asset_id, exc, exc_info=True)
            return {
                "error": f"Context assembly failed: {exc}",
                "organization_id": str(organization_id),
                "entity_id": str(asset_id),
            }

    # =========================================================================
    # EXPOSURE CONTEXT
    # =========================================================================

    async def get_exposure_context(
        self,
        organization_id: UUID,
        exposure_id: UUID,
    ) -> dict[str, Any]:
        """
        Retrieve and assemble full investigation context for an exposure.
        """
        try:
            return await self._builder.build_exposure_context(organization_id, exposure_id)
        except Exception as exc:
            logger.error("Exposure context assembly failed: %s", exc, exc_info=True)
            return {
                "error": f"Context assembly failed: {exc}",
                "organization_id": str(organization_id),
                "entity_id": str(exposure_id),
            }

    # =========================================================================
    # GRAPH CONTEXT
    # =========================================================================

    async def get_graph_context(
        self,
        organization_id: UUID,
    ) -> dict[str, Any]:
        """
        Retrieve the high-level graph topology context for an organisation.
        """
        try:
            return await self._builder.build_graph_context(organization_id)
        except Exception as exc:
            logger.error("Graph context assembly failed: %s", exc, exc_info=True)
            return {
                "error": f"Context assembly failed: {exc}",
                "organization_id": str(organization_id),
            }

    # =========================================================================
    # HISTORICAL CONTEXT
    # =========================================================================

    async def retrieve_historical_context(
        self,
        organization_id: UUID,
        days: int = 30,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Retrieve historical change events and exposure trends for an organisation.

        Returns a plain dict safe for embedding in AI prompts or API responses.

        Parameters
        ----------
        days :
            Rolling window in days.
        limit :
            Maximum change events to return.

        Returns
        -------
        dict with:
            change_events       – recent ChangeEvent records (sanitised)
            exposure_trends     – daily new/resolved exposure counts
            risk_direction      – "improving" | "worsening" | "stable"
            summary             – one-line summary of historical activity
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Recent change events
        chg_stmt = (
            select(ChangeEvent)
            .where(
                and_(
                    ChangeEvent.organization_id == organization_id,
                    ChangeEvent.detected_at >= since,
                )
            )
            .order_by(desc(ChangeEvent.detected_at))
            .limit(limit)
        )
        chg_result = await self.db.execute(chg_stmt)
        events = chg_result.scalars().all()

        change_events = [
            {
                "change_type": str(e.change_type),
                "severity": str(e.severity),
                "change_score": round(e.change_score or 0, 2),
                "detected_at": e.detected_at.strftime("%Y-%m-%d") if e.detected_at else None,
            }
            for e in events
        ]

        # Count new vs resolved exposures per day
        daily_new: dict[str, int] = {}
        daily_resolved: dict[str, int] = {}
        for e in events:
            if not e.detected_at:
                continue
            day = e.detected_at.strftime("%Y-%m-%d")
            ct = str(e.change_type)
            if ct in ("new_exposure", "new_asset"):
                daily_new[day] = daily_new.get(day, 0) + 1
            elif ct in ("resolved_exposure", "removed_asset"):
                daily_resolved[day] = daily_resolved.get(day, 0) + 1

        exposure_trends = [
            {
                "date": day,
                "new": daily_new.get(day, 0),
                "resolved": daily_resolved.get(day, 0),
                "net": daily_new.get(day, 0) - daily_resolved.get(day, 0),
            }
            for day in sorted(set(list(daily_new.keys()) + list(daily_resolved.keys())))
        ]

        # Risk direction
        total_new = sum(daily_new.values())
        total_resolved = sum(daily_resolved.values())
        if total_resolved > total_new:
            direction = "improving"
        elif total_new > total_resolved:
            direction = "worsening"
        else:
            direction = "stable"

        summary = (
            f"Last {days} days: {len(events)} change events. "
            f"{total_new} new exposures/assets, {total_resolved} resolved. "
            f"Trend: {direction}."
        )

        return {
            "organization_id": str(organization_id),
            "window_days": days,
            "change_events": change_events,
            "exposure_trends": exposure_trends,
            "risk_direction": direction,
            "total_new": total_new,
            "total_resolved": total_resolved,
            "summary": summary,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # FINDING CONTEXT
    # =========================================================================

    async def get_finding_context(
        self,
        organization_id: UUID,
        finding_id: UUID,
    ) -> dict[str, Any]:
        """Retrieve and assemble investigation context for a finding."""
        try:
            return await self._builder.build_finding_context(organization_id, finding_id)
        except Exception as exc:
            logger.error("Finding context assembly failed: %s", exc, exc_info=True)
            return {
                "error": f"Context assembly failed: {exc}",
                "organization_id": str(organization_id),
                "entity_id": str(finding_id),
            }
