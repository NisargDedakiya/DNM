"""
Snapshot Service: generates and retrieves immutable recon snapshots.

Responsibilities
----------------
- Serialize current attack surface state into JSON payloads.
- Persist snapshots with append-only writes (never UPDATE or DELETE).
- Provide retrieval helpers for latest snapshot and historical history.

Security guarantees
-------------------
- Every read query filters on organization_id to enforce workspace isolation.
- No row is ever mutated after initial insert.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.recon_snapshot import ReconSnapshot, SnapshotType
from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.technology import Technology
from backend.models.exposure import Exposure
from backend.models.finding import Finding

logger = logging.getLogger(__name__)


class SnapshotService:
    """
    Service for creating and retrieving immutable recon snapshots.

    All write operations are INSERT-only.  No UPDATE or DELETE statements
    are used in this service to preserve timeline integrity.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    # CREATE SNAPSHOT
    # =========================================================================

    async def create_snapshot(
        self,
        organization_id: UUID,
        snapshot_type: SnapshotType | str,
        snapshot_data: list[dict[str, Any]],
        program_id: UUID | None = None,
        trigger_source: str = "monitoring_scan",
        triggered_by_scan_id: UUID | None = None,
        notes: str | None = None,
    ) -> ReconSnapshot:
        """
        Persist an immutable recon snapshot.

        Parameters
        ----------
        organization_id :
            Workspace owner – used for isolation.
        snapshot_type :
            Domain category (assets, endpoints, technologies, exposures, findings).
        snapshot_data :
            Fully serialised list of records captured at this point in time.
        program_id :
            Optional program scope.
        trigger_source :
            What caused this snapshot: "monitoring_scan", "manual", "scheduled", "delta".
        triggered_by_scan_id :
            Scan ID for traceability when triggered by an automated scan.
        notes :
            Optional human-readable context for the snapshot.

        Returns
        -------
        ReconSnapshot
            The newly persisted (immutable) snapshot.
        """
        snapshot = ReconSnapshot(
            organization_id=organization_id,
            program_id=program_id,
            snapshot_type=SnapshotType(snapshot_type) if isinstance(snapshot_type, str) else snapshot_type,
            snapshot_data={
                "records": snapshot_data,
                "record_count": len(snapshot_data),
                "captured_at": datetime.utcnow().isoformat(),
            },
            trigger_source=trigger_source,
            triggered_by_scan_id=triggered_by_scan_id,
            notes=notes,
        )
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)

        logger.info(
            "Snapshot created: id=%s type=%s org=%s records=%d",
            snapshot.id,
            snapshot.snapshot_type,
            organization_id,
            len(snapshot_data),
        )
        return snapshot

    # =========================================================================
    # AUTO-CAPTURE FROM LIVE DATA
    # =========================================================================

    async def create_assets_snapshot(
        self,
        organization_id: UUID,
        program_id: UUID | None = None,
        trigger_source: str = "monitoring_scan",
        triggered_by_scan_id: UUID | None = None,
    ) -> ReconSnapshot:
        """
        Read current Asset rows and persist as an immutable assets snapshot.

        Fetches all assets for the org/program, serialises them, and calls
        ``create_snapshot``.  This is the primary integration point for
        monitoring scans.
        """
        stmt = select(Asset).where(Asset.organization_id == organization_id)
        if program_id:
            stmt = stmt.where(Asset.program_id == program_id)

        result = await self.db.execute(stmt)
        assets = result.scalars().all()

        records = [
            {
                "id": str(a.id),
                "hostname": a.hostname,
                "ip_address": a.ip_address,
                "is_alive": a.is_alive,
                "risk_score": a.risk_score,
                "first_seen": a.first_seen.isoformat() if a.first_seen else None,
                "last_seen": a.last_seen.isoformat() if a.last_seen else None,
            }
            for a in assets
        ]
        return await self.create_snapshot(
            organization_id=organization_id,
            program_id=program_id,
            snapshot_type=SnapshotType.ASSETS,
            snapshot_data=records,
            trigger_source=trigger_source,
            triggered_by_scan_id=triggered_by_scan_id,
        )

    async def create_endpoints_snapshot(
        self,
        organization_id: UUID,
        program_id: UUID | None = None,
        trigger_source: str = "monitoring_scan",
        triggered_by_scan_id: UUID | None = None,
    ) -> ReconSnapshot:
        """Capture current endpoint inventory as an immutable snapshot."""
        # Join through assets to filter by org
        asset_stmt = select(Asset.id).where(Asset.organization_id == organization_id)
        if program_id:
            asset_stmt = asset_stmt.where(Asset.program_id == program_id)

        asset_result = await self.db.execute(asset_stmt)
        asset_ids = [row[0] for row in asset_result.all()]

        if not asset_ids:
            return await self.create_snapshot(
                organization_id=organization_id,
                program_id=program_id,
                snapshot_type=SnapshotType.ENDPOINTS,
                snapshot_data=[],
                trigger_source=trigger_source,
                triggered_by_scan_id=triggered_by_scan_id,
            )

        ep_stmt = select(Endpoint).where(Endpoint.asset_id.in_(asset_ids))
        ep_result = await self.db.execute(ep_stmt)
        endpoints = ep_result.scalars().all()

        records = [
            {
                "id": str(e.id),
                "asset_id": str(e.asset_id),
                "path": e.path,
                "method": e.method,
                "status_code": e.status_code,
                "content_type": e.content_type,
                "first_seen": e.first_seen.isoformat() if e.first_seen else None,
                "last_seen": e.last_seen.isoformat() if e.last_seen else None,
            }
            for e in endpoints
        ]
        return await self.create_snapshot(
            organization_id=organization_id,
            program_id=program_id,
            snapshot_type=SnapshotType.ENDPOINTS,
            snapshot_data=records,
            trigger_source=trigger_source,
            triggered_by_scan_id=triggered_by_scan_id,
        )

    async def create_technologies_snapshot(
        self,
        organization_id: UUID,
        program_id: UUID | None = None,
        trigger_source: str = "monitoring_scan",
        triggered_by_scan_id: UUID | None = None,
    ) -> ReconSnapshot:
        """Capture detected technologies as an immutable snapshot."""
        asset_stmt = select(Asset.id).where(Asset.organization_id == organization_id)
        if program_id:
            asset_stmt = asset_stmt.where(Asset.program_id == program_id)
        asset_result = await self.db.execute(asset_stmt)
        asset_ids = [row[0] for row in asset_result.all()]

        if not asset_ids:
            return await self.create_snapshot(
                organization_id=organization_id,
                program_id=program_id,
                snapshot_type=SnapshotType.TECHNOLOGIES,
                snapshot_data=[],
                trigger_source=trigger_source,
                triggered_by_scan_id=triggered_by_scan_id,
            )

        tech_stmt = select(Technology).where(Technology.asset_id.in_(asset_ids))
        tech_result = await self.db.execute(tech_stmt)
        technologies = tech_result.scalars().all()

        records = [
            {
                "id": str(t.id),
                "asset_id": str(t.asset_id),
                "name": t.name,
                "version": t.version,
                "confidence_score": t.confidence_score,
                "first_detected": t.first_detected.isoformat() if t.first_detected else None,
            }
            for t in technologies
        ]
        return await self.create_snapshot(
            organization_id=organization_id,
            program_id=program_id,
            snapshot_type=SnapshotType.TECHNOLOGIES,
            snapshot_data=records,
            trigger_source=trigger_source,
            triggered_by_scan_id=triggered_by_scan_id,
        )

    async def create_exposures_snapshot(
        self,
        organization_id: UUID,
        program_id: UUID | None = None,
        trigger_source: str = "monitoring_scan",
        triggered_by_scan_id: UUID | None = None,
    ) -> ReconSnapshot:
        """Capture active exposures as an immutable snapshot."""
        stmt = select(Exposure).where(
            and_(
                Exposure.organization_id == organization_id,
                Exposure.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        exposures = result.scalars().all()

        records = [
            {
                "id": str(e.id),
                "asset_id": str(e.asset_id),
                "exposure_type": e.exposure_type,
                "risk_level": e.risk_level,
                "risk_score": e.risk_score,
                "title": e.title,
                "confidence_score": e.confidence_score,
                "first_detected": e.first_detected.isoformat() if e.first_detected else None,
                "last_detected": e.last_detected.isoformat() if e.last_detected else None,
                "remediation_status": e.remediation_status,
            }
            for e in exposures
        ]
        return await self.create_snapshot(
            organization_id=organization_id,
            program_id=program_id,
            snapshot_type=SnapshotType.EXPOSURES,
            snapshot_data=records,
            trigger_source=trigger_source,
            triggered_by_scan_id=triggered_by_scan_id,
        )

    async def create_full_surface_snapshot(
        self,
        organization_id: UUID,
        program_id: UUID | None = None,
        trigger_source: str = "monitoring_scan",
        triggered_by_scan_id: UUID | None = None,
    ) -> dict[str, ReconSnapshot]:
        """
        Capture all five snapshot domains in one atomic call.

        Returns a dict keyed by SnapshotType value.  Useful for monitoring
        scans that need a complete before/after picture.
        """
        snapshots = {}
        for domain_fn, domain_key in [
            (self.create_assets_snapshot, "assets"),
            (self.create_endpoints_snapshot, "endpoints"),
            (self.create_technologies_snapshot, "technologies"),
            (self.create_exposures_snapshot, "exposures"),
        ]:
            snap = await domain_fn(
                organization_id=organization_id,
                program_id=program_id,
                trigger_source=trigger_source,
                triggered_by_scan_id=triggered_by_scan_id,
            )
            snapshots[domain_key] = snap

        logger.info(
            "Full surface snapshot created for org=%s program=%s",
            organization_id,
            program_id,
        )
        return snapshots

    # =========================================================================
    # RETRIEVE LATEST SNAPSHOT
    # =========================================================================

    async def get_latest_snapshot(
        self,
        organization_id: UUID,
        snapshot_type: SnapshotType | str,
        program_id: UUID | None = None,
    ) -> ReconSnapshot | None:
        """
        Retrieve the most recent snapshot for a given type and scope.

        Parameters
        ----------
        organization_id :
            Workspace isolation filter.
        snapshot_type :
            Domain to retrieve (assets, endpoints, technologies, exposures, findings).
        program_id :
            Optional program filter.

        Returns
        -------
        ReconSnapshot | None
        """
        type_enum = SnapshotType(snapshot_type) if isinstance(snapshot_type, str) else snapshot_type

        conditions = [
            ReconSnapshot.organization_id == organization_id,
            ReconSnapshot.snapshot_type == type_enum,
        ]
        if program_id is not None:
            conditions.append(ReconSnapshot.program_id == program_id)

        stmt = (
            select(ReconSnapshot)
            .where(and_(*conditions))
            .order_by(desc(ReconSnapshot.created_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # =========================================================================
    # RETRIEVE SNAPSHOT HISTORY
    # =========================================================================

    async def retrieve_snapshot_history(
        self,
        organization_id: UUID,
        snapshot_type: SnapshotType | str | None = None,
        program_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ReconSnapshot]:
        """
        Retrieve a time-ordered list of historical snapshots.

        Parameters
        ----------
        organization_id :
            Workspace isolation filter – always required.
        snapshot_type :
            Optional domain filter.
        program_id :
            Optional program filter.
        limit : int
            Maximum rows to return (default 50, max enforced by caller).
        offset : int
            Pagination offset.
        since : datetime | None
            Only snapshots at or after this time.
        until : datetime | None
            Only snapshots at or before this time.

        Returns
        -------
        list[ReconSnapshot]
            Ordered newest-first.
        """
        conditions = [ReconSnapshot.organization_id == organization_id]

        if snapshot_type is not None:
            type_enum = SnapshotType(snapshot_type) if isinstance(snapshot_type, str) else snapshot_type
            conditions.append(ReconSnapshot.snapshot_type == type_enum)

        if program_id is not None:
            conditions.append(ReconSnapshot.program_id == program_id)

        if since is not None:
            conditions.append(ReconSnapshot.created_at >= since)

        if until is not None:
            conditions.append(ReconSnapshot.created_at <= until)

        stmt = (
            select(ReconSnapshot)
            .where(and_(*conditions))
            .order_by(desc(ReconSnapshot.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_snapshot_by_id(
        self,
        snapshot_id: UUID,
        organization_id: UUID,
    ) -> ReconSnapshot | None:
        """
        Fetch a specific snapshot by ID with workspace isolation check.

        Always pass ``organization_id`` to prevent cross-tenant access.
        """
        stmt = select(ReconSnapshot).where(
            and_(
                ReconSnapshot.id == snapshot_id,
                ReconSnapshot.organization_id == organization_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_preceding_snapshot(
        self,
        organization_id: UUID,
        snapshot_type: SnapshotType | str,
        before_snapshot_id: UUID,
        program_id: UUID | None = None,
    ) -> ReconSnapshot | None:
        """
        Retrieve the snapshot that immediately precedes the given snapshot.

        Used by the change detection service to build before/after pairs.
        """
        # First fetch the reference snapshot to get its timestamp
        reference = await self.get_snapshot_by_id(before_snapshot_id, organization_id)
        if reference is None:
            return None

        type_enum = SnapshotType(snapshot_type) if isinstance(snapshot_type, str) else snapshot_type

        conditions = [
            ReconSnapshot.organization_id == organization_id,
            ReconSnapshot.snapshot_type == type_enum,
            ReconSnapshot.created_at < reference.created_at,
        ]
        if program_id is not None:
            conditions.append(ReconSnapshot.program_id == program_id)

        stmt = (
            select(ReconSnapshot)
            .where(and_(*conditions))
            .order_by(desc(ReconSnapshot.created_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
