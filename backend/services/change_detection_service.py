"""
Change Detection Service: compares successive recon snapshots to surface drift.

Responsibilities
----------------
- Diff two asset snapshots  → detect new / removed hosts.
- Diff two endpoint snapshots → detect new / removed URL paths.
- Diff two technology snapshots → detect framework / version drift.
- Diff two exposure snapshots → detect new / resolved / changed exposures.

Design rules
------------
- ALL detected changes are persisted as immutable ChangeEvent rows.
- Source and target snapshot IDs are always recorded for auditability.
- Severity is automatically scored based on change context.
- No original data is mutated by this service.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.change_event import ChangeEvent, ChangeType, ChangeSeverity
from backend.models.recon_snapshot import ReconSnapshot, SnapshotType
from backend.services.snapshot_service import SnapshotService

logger = logging.getLogger(__name__)

# ── Severity scoring helpers ────────────────────────────────────────────────

_RISK_TO_SEVERITY: dict[str, ChangeSeverity] = {
    "critical": ChangeSeverity.CRITICAL,
    "high": ChangeSeverity.HIGH,
    "medium": ChangeSeverity.MEDIUM,
    "low": ChangeSeverity.LOW,
    "info": ChangeSeverity.INFO,
}

_SEVERITY_SCORES: dict[ChangeSeverity, float] = {
    ChangeSeverity.CRITICAL: 90.0,
    ChangeSeverity.HIGH: 70.0,
    ChangeSeverity.MEDIUM: 45.0,
    ChangeSeverity.LOW: 20.0,
    ChangeSeverity.INFO: 5.0,
}


def _risk_level_to_severity(risk_level: str | None) -> ChangeSeverity:
    """Map an exposure risk_level string to ChangeSeverity."""
    if risk_level is None:
        return ChangeSeverity.INFO
    return _RISK_TO_SEVERITY.get(risk_level.lower(), ChangeSeverity.INFO)


class ChangeDetectionService:
    """
    Service that diffs successive recon snapshots and persists ChangeEvents.

    All public ``detect_*`` methods accept explicit before/after snapshot IDs
    so the caller controls which pair is compared.  Each method returns the
    list of ChangeEvent objects it persisted.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._snapshot_svc = SnapshotService(db)

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    async def _persist_event(
        self,
        organization_id: UUID,
        change_type: ChangeType,
        severity: ChangeSeverity,
        previous_value: dict[str, Any] | None,
        new_value: dict[str, Any] | None,
        description: str,
        asset_id: UUID | None = None,
        program_id: UUID | None = None,
        source_snapshot_id: UUID | None = None,
        target_snapshot_id: UUID | None = None,
        detected_by_scan_id: UUID | None = None,
    ) -> ChangeEvent:
        """Insert a single immutable ChangeEvent row and return it."""
        event = ChangeEvent(
            organization_id=organization_id,
            program_id=program_id,
            asset_id=asset_id,
            change_type=change_type,
            severity=severity,
            change_score=_SEVERITY_SCORES[severity],
            previous_value=previous_value,
            new_value=new_value,
            description=description,
            source_snapshot_id=source_snapshot_id,
            target_snapshot_id=target_snapshot_id,
            detected_by_scan_id=detected_by_scan_id,
        )
        self.db.add(event)
        return event

    async def _load_snapshot_records(
        self,
        snapshot_id: UUID,
        organization_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        Safely load the 'records' list from a snapshot payload.

        Returns an empty list if the snapshot doesn't exist or has no data.
        Always enforces workspace isolation via ``organization_id``.
        """
        snap = await self._snapshot_svc.get_snapshot_by_id(snapshot_id, organization_id)
        if snap is None:
            logger.warning("Snapshot %s not found for org %s", snapshot_id, organization_id)
            return []
        data = snap.snapshot_data
        if isinstance(data, dict):
            return data.get("records", [])
        return []

    # =========================================================================
    # ASSET CHANGE DETECTION
    # =========================================================================

    async def detect_asset_changes(
        self,
        organization_id: UUID,
        source_snapshot_id: UUID,
        target_snapshot_id: UUID,
        program_id: UUID | None = None,
        detected_by_scan_id: UUID | None = None,
    ) -> list[ChangeEvent]:
        """
        Compare two asset snapshots and persist new/removed asset events.

        Algorithm
        ---------
        - Key assets by hostname (unique identifier within a program scope).
        - Hostnames in target but not source → NEW_ASSET (severity=HIGH).
        - Hostnames in source but not target → REMOVED_ASSET (severity=MEDIUM).
        - Commit all events in one transaction.

        Returns
        -------
        list[ChangeEvent]
            All persisted change events for this diff pair.
        """
        source_records = await self._load_snapshot_records(source_snapshot_id, organization_id)
        target_records = await self._load_snapshot_records(target_snapshot_id, organization_id)

        source_map = {r["hostname"]: r for r in source_records}
        target_map = {r["hostname"]: r for r in target_records}

        events: list[ChangeEvent] = []

        # New assets
        for hostname, record in target_map.items():
            if hostname not in source_map:
                evt = await self._persist_event(
                    organization_id=organization_id,
                    change_type=ChangeType.NEW_ASSET,
                    severity=ChangeSeverity.HIGH,
                    previous_value=None,
                    new_value=record,
                    description=f"New asset detected: {hostname} (IP: {record.get('ip_address', 'unknown')})",
                    program_id=program_id,
                    source_snapshot_id=source_snapshot_id,
                    target_snapshot_id=target_snapshot_id,
                    detected_by_scan_id=detected_by_scan_id,
                )
                events.append(evt)

        # Removed assets
        for hostname, record in source_map.items():
            if hostname not in target_map:
                evt = await self._persist_event(
                    organization_id=organization_id,
                    change_type=ChangeType.REMOVED_ASSET,
                    severity=ChangeSeverity.MEDIUM,
                    previous_value=record,
                    new_value=None,
                    description=f"Asset disappeared from attack surface: {hostname}",
                    program_id=program_id,
                    source_snapshot_id=source_snapshot_id,
                    target_snapshot_id=target_snapshot_id,
                    detected_by_scan_id=detected_by_scan_id,
                )
                events.append(evt)

        await self.db.commit()
        logger.info(
            "Asset diff: org=%s new=%d removed=%d",
            organization_id,
            sum(1 for e in events if e.change_type == ChangeType.NEW_ASSET),
            sum(1 for e in events if e.change_type == ChangeType.REMOVED_ASSET),
        )
        return events

    # =========================================================================
    # ENDPOINT CHANGE DETECTION
    # =========================================================================

    async def detect_endpoint_changes(
        self,
        organization_id: UUID,
        source_snapshot_id: UUID,
        target_snapshot_id: UUID,
        program_id: UUID | None = None,
        detected_by_scan_id: UUID | None = None,
    ) -> list[ChangeEvent]:
        """
        Compare two endpoint snapshots and persist new/removed endpoint events.

        Keys endpoints by (asset_id, method, path) tuple.
        """
        source_records = await self._load_snapshot_records(source_snapshot_id, organization_id)
        target_records = await self._load_snapshot_records(target_snapshot_id, organization_id)

        def _key(r: dict) -> str:
            return f"{r.get('asset_id', '')}::{r.get('method', 'GET')}::{r.get('path', '')}"

        source_map = {_key(r): r for r in source_records}
        target_map = {_key(r): r for r in target_records}

        events: list[ChangeEvent] = []

        # New endpoints
        for key, record in target_map.items():
            if key not in source_map:
                asset_id_raw = record.get("asset_id")
                evt = await self._persist_event(
                    organization_id=organization_id,
                    change_type=ChangeType.NEW_ENDPOINT,
                    severity=ChangeSeverity.MEDIUM,
                    previous_value=None,
                    new_value=record,
                    description=(
                        f"New endpoint discovered: {record.get('method', 'GET')} "
                        f"{record.get('path', '?')} (status={record.get('status_code', '?')})"
                    ),
                    asset_id=UUID(asset_id_raw) if asset_id_raw else None,
                    program_id=program_id,
                    source_snapshot_id=source_snapshot_id,
                    target_snapshot_id=target_snapshot_id,
                    detected_by_scan_id=detected_by_scan_id,
                )
                events.append(evt)

        # Removed endpoints
        for key, record in source_map.items():
            if key not in target_map:
                asset_id_raw = record.get("asset_id")
                evt = await self._persist_event(
                    organization_id=organization_id,
                    change_type=ChangeType.REMOVED_ENDPOINT,
                    severity=ChangeSeverity.LOW,
                    previous_value=record,
                    new_value=None,
                    description=(
                        f"Endpoint removed: {record.get('method', 'GET')} "
                        f"{record.get('path', '?')}"
                    ),
                    asset_id=UUID(asset_id_raw) if asset_id_raw else None,
                    program_id=program_id,
                    source_snapshot_id=source_snapshot_id,
                    target_snapshot_id=target_snapshot_id,
                    detected_by_scan_id=detected_by_scan_id,
                )
                events.append(evt)

        await self.db.commit()
        logger.info(
            "Endpoint diff: org=%s new=%d removed=%d",
            organization_id,
            sum(1 for e in events if e.change_type == ChangeType.NEW_ENDPOINT),
            sum(1 for e in events if e.change_type == ChangeType.REMOVED_ENDPOINT),
        )
        return events

    # =========================================================================
    # TECHNOLOGY CHANGE DETECTION
    # =========================================================================

    async def detect_technology_changes(
        self,
        organization_id: UUID,
        source_snapshot_id: UUID,
        target_snapshot_id: UUID,
        program_id: UUID | None = None,
        detected_by_scan_id: UUID | None = None,
    ) -> list[ChangeEvent]:
        """
        Detect technology drift between two technology snapshots.

        Detects:
        - New technology appearances on an asset.
        - Technology version upgrades or downgrades.
        - Technology removal from an asset.

        Keys by (asset_id, tech_name).
        """
        source_records = await self._load_snapshot_records(source_snapshot_id, organization_id)
        target_records = await self._load_snapshot_records(target_snapshot_id, organization_id)

        def _key(r: dict) -> str:
            return f"{r.get('asset_id', '')}::{r.get('name', '').lower()}"

        source_map = {_key(r): r for r in source_records}
        target_map = {_key(r): r for r in target_records}

        events: list[ChangeEvent] = []

        # New technologies + version changes
        for key, new_rec in target_map.items():
            asset_id_raw = new_rec.get("asset_id")
            asset_uuid = UUID(asset_id_raw) if asset_id_raw else None

            if key not in source_map:
                evt = await self._persist_event(
                    organization_id=organization_id,
                    change_type=ChangeType.TECHNOLOGY_CHANGE,
                    severity=ChangeSeverity.MEDIUM,
                    previous_value=None,
                    new_value=new_rec,
                    description=(
                        f"New technology detected: {new_rec.get('name')} "
                        f"v{new_rec.get('version', 'unknown')}"
                    ),
                    asset_id=asset_uuid,
                    program_id=program_id,
                    source_snapshot_id=source_snapshot_id,
                    target_snapshot_id=target_snapshot_id,
                    detected_by_scan_id=detected_by_scan_id,
                )
                events.append(evt)
            else:
                old_rec = source_map[key]
                old_version = old_rec.get("version")
                new_version = new_rec.get("version")
                if old_version != new_version:
                    evt = await self._persist_event(
                        organization_id=organization_id,
                        change_type=ChangeType.TECHNOLOGY_CHANGE,
                        severity=ChangeSeverity.HIGH,
                        previous_value=old_rec,
                        new_value=new_rec,
                        description=(
                            f"Technology version change: {new_rec.get('name')} "
                            f"{old_version} → {new_version}"
                        ),
                        asset_id=asset_uuid,
                        program_id=program_id,
                        source_snapshot_id=source_snapshot_id,
                        target_snapshot_id=target_snapshot_id,
                        detected_by_scan_id=detected_by_scan_id,
                    )
                    events.append(evt)

        # Removed technologies
        for key, old_rec in source_map.items():
            if key not in target_map:
                asset_id_raw = old_rec.get("asset_id")
                evt = await self._persist_event(
                    organization_id=organization_id,
                    change_type=ChangeType.TECHNOLOGY_CHANGE,
                    severity=ChangeSeverity.LOW,
                    previous_value=old_rec,
                    new_value=None,
                    description=f"Technology removed: {old_rec.get('name')}",
                    asset_id=UUID(asset_id_raw) if asset_id_raw else None,
                    program_id=program_id,
                    source_snapshot_id=source_snapshot_id,
                    target_snapshot_id=target_snapshot_id,
                    detected_by_scan_id=detected_by_scan_id,
                )
                events.append(evt)

        await self.db.commit()
        logger.info(
            "Technology diff: org=%s events=%d",
            organization_id,
            len(events),
        )
        return events

    # =========================================================================
    # EXPOSURE CHANGE DETECTION
    # =========================================================================

    async def detect_exposure_changes(
        self,
        organization_id: UUID,
        source_snapshot_id: UUID,
        target_snapshot_id: UUID,
        program_id: UUID | None = None,
        detected_by_scan_id: UUID | None = None,
    ) -> list[ChangeEvent]:
        """
        Detect exposure evolution between two exposure snapshots.

        Detects:
        - NEW_EXPOSURE: exposure appeared for the first time.
        - RESOLVED_EXPOSURE: previously active exposure no longer present.
        - EXPOSURE_CHANGE: risk level, remediation status, or risk score changed.

        Keys by exposure ID (since exposures have stable UUIDs).
        """
        source_records = await self._load_snapshot_records(source_snapshot_id, organization_id)
        target_records = await self._load_snapshot_records(target_snapshot_id, organization_id)

        source_map = {r["id"]: r for r in source_records}
        target_map = {r["id"]: r for r in target_records}

        events: list[ChangeEvent] = []

        # New exposures
        for eid, new_rec in target_map.items():
            asset_id_raw = new_rec.get("asset_id")
            if eid not in source_map:
                severity = _risk_level_to_severity(new_rec.get("risk_level"))
                evt = await self._persist_event(
                    organization_id=organization_id,
                    change_type=ChangeType.NEW_EXPOSURE,
                    severity=severity,
                    previous_value=None,
                    new_value=new_rec,
                    description=(
                        f"New exposure detected: [{new_rec.get('risk_level', '?').upper()}] "
                        f"{new_rec.get('title', 'Unknown')}"
                    ),
                    asset_id=UUID(asset_id_raw) if asset_id_raw else None,
                    program_id=program_id,
                    source_snapshot_id=source_snapshot_id,
                    target_snapshot_id=target_snapshot_id,
                    detected_by_scan_id=detected_by_scan_id,
                )
                events.append(evt)
            else:
                # Check for meaningful field changes
                old_rec = source_map[eid]
                changed_fields = []
                if old_rec.get("risk_level") != new_rec.get("risk_level"):
                    changed_fields.append(
                        f"risk_level: {old_rec.get('risk_level')} → {new_rec.get('risk_level')}"
                    )
                if old_rec.get("remediation_status") != new_rec.get("remediation_status"):
                    changed_fields.append(
                        f"remediation: {old_rec.get('remediation_status')} → {new_rec.get('remediation_status')}"
                    )
                old_score = old_rec.get("risk_score", 0)
                new_score = new_rec.get("risk_score", 0)
                if abs(float(old_score) - float(new_score)) >= 5.0:
                    changed_fields.append(f"risk_score: {old_score:.1f} → {new_score:.1f}")

                if changed_fields:
                    severity = _risk_level_to_severity(new_rec.get("risk_level"))
                    evt = await self._persist_event(
                        organization_id=organization_id,
                        change_type=ChangeType.EXPOSURE_CHANGE,
                        severity=severity,
                        previous_value=old_rec,
                        new_value=new_rec,
                        description=(
                            f"Exposure updated [{new_rec.get('title', 'Unknown')}]: "
                            + "; ".join(changed_fields)
                        ),
                        asset_id=UUID(asset_id_raw) if asset_id_raw else None,
                        program_id=program_id,
                        source_snapshot_id=source_snapshot_id,
                        target_snapshot_id=target_snapshot_id,
                        detected_by_scan_id=detected_by_scan_id,
                    )
                    events.append(evt)

        # Resolved exposures
        for eid, old_rec in source_map.items():
            if eid not in target_map:
                asset_id_raw = old_rec.get("asset_id")
                evt = await self._persist_event(
                    organization_id=organization_id,
                    change_type=ChangeType.RESOLVED_EXPOSURE,
                    severity=ChangeSeverity.INFO,
                    previous_value=old_rec,
                    new_value=None,
                    description=(
                        f"Exposure resolved/removed: {old_rec.get('title', 'Unknown')}"
                    ),
                    asset_id=UUID(asset_id_raw) if asset_id_raw else None,
                    program_id=program_id,
                    source_snapshot_id=source_snapshot_id,
                    target_snapshot_id=target_snapshot_id,
                    detected_by_scan_id=detected_by_scan_id,
                )
                events.append(evt)

        await self.db.commit()
        logger.info(
            "Exposure diff: org=%s new=%d changed=%d resolved=%d",
            organization_id,
            sum(1 for e in events if e.change_type == ChangeType.NEW_EXPOSURE),
            sum(1 for e in events if e.change_type == ChangeType.EXPOSURE_CHANGE),
            sum(1 for e in events if e.change_type == ChangeType.RESOLVED_EXPOSURE),
        )
        return events

    # =========================================================================
    # FULL SURFACE DIFF
    # =========================================================================

    async def run_full_surface_diff(
        self,
        organization_id: UUID,
        before_snapshots: dict[str, UUID],
        after_snapshots: dict[str, UUID],
        program_id: UUID | None = None,
        detected_by_scan_id: UUID | None = None,
    ) -> dict[str, list[ChangeEvent]]:
        """
        Run change detection across all domains in one call.

        Parameters
        ----------
        before_snapshots :
            Mapping of domain → snapshot_id for the BEFORE state.
            Expected keys: "assets", "endpoints", "technologies", "exposures".
        after_snapshots :
            Mapping of domain → snapshot_id for the AFTER state.

        Returns
        -------
        dict[str, list[ChangeEvent]]
            Mapping of domain → list of persisted ChangeEvent objects.
        """
        results: dict[str, list[ChangeEvent]] = {}

        if "assets" in before_snapshots and "assets" in after_snapshots:
            results["assets"] = await self.detect_asset_changes(
                organization_id=organization_id,
                source_snapshot_id=before_snapshots["assets"],
                target_snapshot_id=after_snapshots["assets"],
                program_id=program_id,
                detected_by_scan_id=detected_by_scan_id,
            )

        if "endpoints" in before_snapshots and "endpoints" in after_snapshots:
            results["endpoints"] = await self.detect_endpoint_changes(
                organization_id=organization_id,
                source_snapshot_id=before_snapshots["endpoints"],
                target_snapshot_id=after_snapshots["endpoints"],
                program_id=program_id,
                detected_by_scan_id=detected_by_scan_id,
            )

        if "technologies" in before_snapshots and "technologies" in after_snapshots:
            results["technologies"] = await self.detect_technology_changes(
                organization_id=organization_id,
                source_snapshot_id=before_snapshots["technologies"],
                target_snapshot_id=after_snapshots["technologies"],
                program_id=program_id,
                detected_by_scan_id=detected_by_scan_id,
            )

        if "exposures" in before_snapshots and "exposures" in after_snapshots:
            results["exposures"] = await self.detect_exposure_changes(
                organization_id=organization_id,
                source_snapshot_id=before_snapshots["exposures"],
                target_snapshot_id=after_snapshots["exposures"],
                program_id=program_id,
                detected_by_scan_id=detected_by_scan_id,
            )

        total = sum(len(v) for v in results.values())
        logger.info(
            "Full surface diff complete: org=%s total_changes=%d",
            organization_id,
            total,
        )
        return results

    # =========================================================================
    # QUERY HELPERS
    # =========================================================================

    async def get_recent_changes(
        self,
        organization_id: UUID,
        limit: int = 100,
        change_type: ChangeType | str | None = None,
        severity: ChangeSeverity | str | None = None,
    ) -> list[ChangeEvent]:
        """Retrieve recent change events for an organization (newest first)."""
        conditions = [ChangeEvent.organization_id == organization_id]

        if change_type is not None:
            ct = ChangeType(change_type) if isinstance(change_type, str) else change_type
            conditions.append(ChangeEvent.change_type == ct)

        if severity is not None:
            sv = ChangeSeverity(severity) if isinstance(severity, str) else severity
            conditions.append(ChangeEvent.severity == sv)

        stmt = (
            select(ChangeEvent)
            .where(and_(*conditions))
            .order_by(desc(ChangeEvent.detected_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_asset_change_history(
        self,
        organization_id: UUID,
        asset_id: UUID,
        limit: int = 50,
    ) -> list[ChangeEvent]:
        """Retrieve all change events for a specific asset (newest first)."""
        stmt = (
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
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
