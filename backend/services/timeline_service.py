"""
Timeline Service: builds historical exposure timelines and analytics.

Responsibilities
----------------
- Generate per-asset timelines combining snapshot history and change events.
- Build org-level exposure timelines showing risk evolution over time.
- Assemble a full change history feed with filtering and pagination.
- Produce attack surface analytics: growth, risk drift, tech evolution.

Design rules
------------
- All queries filter on organization_id for strict workspace isolation.
- No data is mutated; this service is purely read-oriented.
- Returned structures are plain dicts suitable for JSON serialisation.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, desc, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.change_event import ChangeEvent, ChangeType, ChangeSeverity
from backend.models.recon_snapshot import ReconSnapshot, SnapshotType
from backend.models.asset import Asset
from backend.models.exposure import Exposure

logger = logging.getLogger(__name__)


class TimelineService:
    """
    Service for building historical intelligence timelines and analytics.

    All methods return plain dicts/lists – no ORM objects – to keep the
    API layer simple and avoid lazy-load traps in async context.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    # ASSET TIMELINE
    # =========================================================================

    async def generate_asset_timeline(
        self,
        organization_id: UUID,
        asset_id: UUID,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Build a comprehensive timeline for a single asset.

        Combines:
        1. Asset metadata (first_seen, last_seen, risk_score).
        2. All ChangeEvents affecting this asset (newest first).
        3. Summary of change type counts.

        Parameters
        ----------
        organization_id :
            Workspace isolation filter.
        asset_id :
            Target asset.
        limit :
            Max change events to return.

        Returns
        -------
        dict with keys:
            asset         – dict of asset fields
            timeline      – list of change event dicts (newest first)
            summary       – change type count breakdown
            risk_trend    – list of (detected_at, change_score) for charting
        """
        # Fetch asset with workspace isolation
        asset_stmt = select(Asset).where(
            and_(
                Asset.id == asset_id,
                Asset.organization_id == organization_id,
            )
        )
        asset_result = await self.db.execute(asset_stmt)
        asset = asset_result.scalars().first()

        if asset is None:
            return {
                "asset": None,
                "timeline": [],
                "summary": {},
                "risk_trend": [],
                "error": "Asset not found or access denied",
            }

        # Fetch change events for this asset
        event_stmt = (
            select(ChangeEvent)
            .where(
                and_(
                    ChangeEvent.organization_id == organization_id,
                    ChangeEvent.asset_id == asset_id,
                )
            )
            .order_by(desc(ChangeEvent.detected_at))
            .limit(limit)
        )
        event_result = await self.db.execute(event_stmt)
        events = event_result.scalars().all()

        # Build timeline entries
        timeline = [
            {
                "event_id": str(e.id),
                "change_type": e.change_type,
                "severity": e.severity,
                "change_score": e.change_score,
                "description": e.description,
                "previous_value": e.previous_value,
                "new_value": e.new_value,
                "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                "source_snapshot_id": str(e.source_snapshot_id) if e.source_snapshot_id else None,
                "target_snapshot_id": str(e.target_snapshot_id) if e.target_snapshot_id else None,
            }
            for e in events
        ]

        # Summary counts by change_type
        summary: dict[str, int] = defaultdict(int)
        for e in events:
            summary[e.change_type] += 1

        # Risk trend: (timestamp, score) pairs for charting
        risk_trend = [
            {"detected_at": e.detected_at.isoformat() if e.detected_at else None, "change_score": e.change_score}
            for e in reversed(events)  # chronological for charts
        ]

        return {
            "asset": {
                "id": str(asset.id),
                "hostname": asset.hostname,
                "ip_address": asset.ip_address,
                "is_alive": asset.is_alive,
                "risk_score": asset.risk_score,
                "first_seen": asset.first_seen.isoformat() if asset.first_seen else None,
                "last_seen": asset.last_seen.isoformat() if asset.last_seen else None,
            },
            "timeline": timeline,
            "summary": dict(summary),
            "risk_trend": risk_trend,
        }

    # =========================================================================
    # EXPOSURE TIMELINE
    # =========================================================================

    async def generate_exposure_timeline(
        self,
        organization_id: UUID,
        days: int = 30,
        asset_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Build an organisation-level exposure evolution timeline.

        Groups exposure-related change events by day to show how the
        attack surface's risk profile evolved over the given window.

        Parameters
        ----------
        organization_id :
            Workspace isolation filter.
        days :
            Lookback window in days (default 30).
        asset_id :
            Optional filter to limit timeline to a single asset.

        Returns
        -------
        dict with keys:
            daily_breakdown  – list of {date, new, resolved, changed, net_risk}
            totals           – aggregate counts for the period
            current_active   – count of currently active exposures
            severity_trend   – daily count per severity level
        """
        since = datetime.utcnow() - timedelta(days=days)

        exposure_change_types = {
            ChangeType.NEW_EXPOSURE,
            ChangeType.RESOLVED_EXPOSURE,
            ChangeType.EXPOSURE_CHANGE,
        }

        conditions = [
            ChangeEvent.organization_id == organization_id,
            ChangeEvent.change_type.in_([ct.value for ct in exposure_change_types]),
            ChangeEvent.detected_at >= since,
        ]
        if asset_id is not None:
            conditions.append(ChangeEvent.asset_id == asset_id)

        stmt = (
            select(ChangeEvent)
            .where(and_(*conditions))
            .order_by(ChangeEvent.detected_at)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        # Daily bucket aggregation
        daily: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"date": None, "new": 0, "resolved": 0, "changed": 0, "net_risk_delta": 0.0}
        )
        severity_trend: dict[str, dict[str, int]] = defaultdict(
            lambda: {s.value: 0 for s in ChangeSeverity}
        )

        totals = {"new": 0, "resolved": 0, "changed": 0}

        for e in events:
            day_key = e.detected_at.strftime("%Y-%m-%d") if e.detected_at else "unknown"
            daily[day_key]["date"] = day_key

            ct = e.change_type
            if ct == ChangeType.NEW_EXPOSURE.value:
                daily[day_key]["new"] += 1
                totals["new"] += 1
                daily[day_key]["net_risk_delta"] += e.change_score
            elif ct == ChangeType.RESOLVED_EXPOSURE.value:
                daily[day_key]["resolved"] += 1
                totals["resolved"] += 1
                daily[day_key]["net_risk_delta"] -= e.change_score
            elif ct == ChangeType.EXPOSURE_CHANGE.value:
                daily[day_key]["changed"] += 1
                totals["changed"] += 1

            severity_trend[day_key][e.severity] = severity_trend[day_key].get(e.severity, 0) + 1

        # Current active exposure count
        active_stmt = select(func.count(Exposure.id)).where(
            and_(
                Exposure.organization_id == organization_id,
                Exposure.is_active == True,
            )
        )
        active_result = await self.db.execute(active_stmt)
        current_active = active_result.scalar() or 0

        # Build sorted daily list
        daily_list = sorted(daily.values(), key=lambda x: x["date"] or "")
        severity_list = [
            {"date": date, **counts}
            for date, counts in sorted(severity_trend.items())
        ]

        return {
            "daily_breakdown": daily_list,
            "totals": totals,
            "current_active": current_active,
            "severity_trend": severity_list,
            "window_days": days,
        }

    # =========================================================================
    # CHANGE HISTORY
    # =========================================================================

    async def build_change_history(
        self,
        organization_id: UUID,
        limit: int = 200,
        offset: int = 0,
        change_type: str | None = None,
        severity: str | None = None,
        asset_id: UUID | None = None,
        program_id: UUID | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Return a paginated, filtered change history feed for an organisation.

        Parameters
        ----------
        organization_id :
            Workspace isolation filter.
        limit / offset :
            Pagination controls.
        change_type :
            Optional filter (e.g. "new_asset", "exposure_change").
        severity :
            Optional filter (e.g. "critical", "high").
        asset_id :
            Optional asset scope.
        program_id :
            Optional program scope.
        since / until :
            Optional time-window filters.

        Returns
        -------
        dict with keys:
            events   – list of change event dicts
            total    – count query result for pagination
            filters  – echo of active filters
        """
        conditions = [ChangeEvent.organization_id == organization_id]

        if change_type is not None:
            conditions.append(ChangeEvent.change_type == change_type)
        if severity is not None:
            conditions.append(ChangeEvent.severity == severity)
        if asset_id is not None:
            conditions.append(ChangeEvent.asset_id == asset_id)
        if program_id is not None:
            conditions.append(ChangeEvent.program_id == program_id)
        if since is not None:
            conditions.append(ChangeEvent.detected_at >= since)
        if until is not None:
            conditions.append(ChangeEvent.detected_at <= until)

        # Count total matching rows for pagination metadata
        count_stmt = select(func.count(ChangeEvent.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Fetch page
        stmt = (
            select(ChangeEvent)
            .where(and_(*conditions))
            .order_by(desc(ChangeEvent.detected_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        event_list = [
            {
                "id": str(e.id),
                "change_type": e.change_type,
                "severity": e.severity,
                "change_score": e.change_score,
                "description": e.description,
                "asset_id": str(e.asset_id) if e.asset_id else None,
                "program_id": str(e.program_id) if e.program_id else None,
                "source_snapshot_id": str(e.source_snapshot_id) if e.source_snapshot_id else None,
                "target_snapshot_id": str(e.target_snapshot_id) if e.target_snapshot_id else None,
                "detected_by_scan_id": str(e.detected_by_scan_id) if e.detected_by_scan_id else None,
                "detected_at": e.detected_at.isoformat() if e.detected_at else None,
            }
            for e in events
        ]

        return {
            "events": event_list,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "change_type": change_type,
                "severity": severity,
                "asset_id": str(asset_id) if asset_id else None,
                "program_id": str(program_id) if program_id else None,
                "since": since.isoformat() if since else None,
                "until": until.isoformat() if until else None,
            },
        }

    # =========================================================================
    # SNAPSHOT HISTORY FEED
    # =========================================================================

    async def get_snapshot_history(
        self,
        organization_id: UUID,
        snapshot_type: str | None = None,
        program_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Return a paginated list of historical snapshots.

        Snapshot data payloads are NOT included in the listing to keep
        responses lightweight – use ``GET /timeline/snapshots/{id}`` to
        fetch a specific snapshot's full payload.
        """
        conditions = [ReconSnapshot.organization_id == organization_id]

        if snapshot_type is not None:
            conditions.append(ReconSnapshot.snapshot_type == snapshot_type)
        if program_id is not None:
            conditions.append(ReconSnapshot.program_id == program_id)

        count_stmt = select(func.count(ReconSnapshot.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = (
            select(ReconSnapshot)
            .where(and_(*conditions))
            .order_by(desc(ReconSnapshot.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        snapshots = result.scalars().all()

        snapshot_list = [
            {
                "id": str(s.id),
                "snapshot_type": s.snapshot_type,
                "program_id": str(s.program_id) if s.program_id else None,
                "trigger_source": s.trigger_source,
                "triggered_by_scan_id": str(s.triggered_by_scan_id) if s.triggered_by_scan_id else None,
                "record_count": (
                    s.snapshot_data.get("record_count", 0)
                    if isinstance(s.snapshot_data, dict)
                    else 0
                ),
                "notes": s.notes,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in snapshots
        ]

        return {
            "snapshots": snapshot_list,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # =========================================================================
    # ATTACK SURFACE ANALYTICS
    # =========================================================================

    async def get_attack_surface_analytics(
        self,
        organization_id: UUID,
        days: int = 90,
    ) -> dict[str, Any]:
        """
        Generate high-level attack surface growth and risk drift analytics.

        Returns
        -------
        dict with keys:
            asset_growth        – new vs removed assets per week
            risk_drift          – net risk score movement over time
            technology_churn    – number of tech changes per week
            exposure_evolution  – active exposure count at each snapshot point
            top_changed_assets  – assets with highest change event count
        """
        since = datetime.utcnow() - timedelta(days=days)

        # --- Asset growth (new vs removed per week) ---
        asset_types = [ChangeType.NEW_ASSET.value, ChangeType.REMOVED_ASSET.value]
        asset_stmt = (
            select(ChangeEvent)
            .where(
                and_(
                    ChangeEvent.organization_id == organization_id,
                    ChangeEvent.change_type.in_(asset_types),
                    ChangeEvent.detected_at >= since,
                )
            )
            .order_by(ChangeEvent.detected_at)
        )
        asset_events = (await self.db.execute(asset_stmt)).scalars().all()

        weekly_assets: dict[str, dict[str, int]] = defaultdict(lambda: {"new": 0, "removed": 0})
        for e in asset_events:
            if e.detected_at:
                wk = e.detected_at.strftime("%Y-W%W")
                if e.change_type == ChangeType.NEW_ASSET.value:
                    weekly_assets[wk]["new"] += 1
                else:
                    weekly_assets[wk]["removed"] += 1

        asset_growth = [
            {"week": wk, **counts}
            for wk, counts in sorted(weekly_assets.items())
        ]

        # --- Technology churn per week ---
        tech_stmt = (
            select(ChangeEvent)
            .where(
                and_(
                    ChangeEvent.organization_id == organization_id,
                    ChangeEvent.change_type == ChangeType.TECHNOLOGY_CHANGE.value,
                    ChangeEvent.detected_at >= since,
                )
            )
        )
        tech_events = (await self.db.execute(tech_stmt)).scalars().all()

        weekly_tech: dict[str, int] = defaultdict(int)
        for e in tech_events:
            if e.detected_at:
                wk = e.detected_at.strftime("%Y-W%W")
                weekly_tech[wk] += 1

        technology_churn = [
            {"week": wk, "changes": cnt}
            for wk, cnt in sorted(weekly_tech.items())
        ]

        # --- Risk drift: rolling net risk score change ---
        risk_stmt = (
            select(ChangeEvent)
            .where(
                and_(
                    ChangeEvent.organization_id == organization_id,
                    ChangeEvent.detected_at >= since,
                )
            )
            .order_by(ChangeEvent.detected_at)
        )
        risk_events = (await self.db.execute(risk_stmt)).scalars().all()

        risk_drift_by_week: dict[str, float] = defaultdict(float)
        for e in risk_events:
            if e.detected_at:
                wk = e.detected_at.strftime("%Y-W%W")
                # New threats add risk, resolutions subtract
                if e.change_type in {ChangeType.NEW_ASSET.value, ChangeType.NEW_EXPOSURE.value}:
                    risk_drift_by_week[wk] += e.change_score
                elif e.change_type in {ChangeType.REMOVED_ASSET.value, ChangeType.RESOLVED_EXPOSURE.value}:
                    risk_drift_by_week[wk] -= e.change_score

        risk_drift = [
            {"week": wk, "net_risk_delta": round(delta, 2)}
            for wk, delta in sorted(risk_drift_by_week.items())
        ]

        # --- Top changed assets ---
        top_assets_stmt = (
            select(
                ChangeEvent.asset_id,
                func.count(ChangeEvent.id).label("change_count"),
            )
            .where(
                and_(
                    ChangeEvent.organization_id == organization_id,
                    ChangeEvent.asset_id.isnot(None),
                    ChangeEvent.detected_at >= since,
                )
            )
            .group_by(ChangeEvent.asset_id)
            .order_by(desc("change_count"))
            .limit(10)
        )
        top_assets_result = await self.db.execute(top_assets_stmt)
        top_changed_assets = [
            {"asset_id": str(row[0]), "change_count": row[1]}
            for row in top_assets_result.all()
        ]

        # --- Current exposure count by risk level ---
        exposure_dist_stmt = (
            select(Exposure.risk_level, func.count(Exposure.id))
            .where(
                and_(
                    Exposure.organization_id == organization_id,
                    Exposure.is_active == True,
                )
            )
            .group_by(Exposure.risk_level)
        )
        exp_result = await self.db.execute(exposure_dist_stmt)
        exposure_distribution = {row[0]: row[1] for row in exp_result.all()}

        return {
            "asset_growth": asset_growth,
            "technology_churn": technology_churn,
            "risk_drift": risk_drift,
            "top_changed_assets": top_changed_assets,
            "exposure_distribution": exposure_distribution,
            "analytics_window_days": days,
            "generated_at": datetime.utcnow().isoformat(),
        }
