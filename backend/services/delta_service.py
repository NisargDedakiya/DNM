"""
Delta service for comparing recon snapshots and detecting changes.
Analyzes differences between scans to identify new/removed assets and findings.
"""
from __future__ import annotations

from uuid import UUID
from typing import Optional
from datetime import datetime

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.scan import Scan, ScanStatus
from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.finding import Finding, SeverityLevel
from backend.models.technology import Technology


class DeltaAnalysis:
    """Data class for delta analysis results."""

    def __init__(self):
        self.new_assets: list[dict] = []
        self.removed_assets: list[dict] = []
        self.new_endpoints: list[dict] = []
        self.removed_endpoints: list[dict] = []
        self.new_findings: list[dict] = []
        self.removed_findings: list[dict] = []
        self.critical_findings: list[dict] = []
        self.summary: dict = {}


class DeltaService:
    """Service for analyzing differences between recon scans."""

    def __init__(self, db: AsyncSession):
        """Initialize delta service with database session."""
        self.db = db

    async def generate_delta_report(
        self,
        program_id: UUID,
        current_scan_id: UUID,
        baseline_scan_id: Optional[UUID] = None,
    ) -> DeltaAnalysis:
        """
        Generate delta analysis between current and baseline scans.

        Args:
            program_id: Program ID
            current_scan_id: Current scan to analyze
            baseline_scan_id: Baseline scan for comparison (latest before current if None)

        Returns:
            DeltaAnalysis: Analysis results
        """
        # Get baseline scan if not specified
        if baseline_scan_id is None:
            baseline_scan_id = await self._get_previous_completed_scan(
                program_id, current_scan_id
            )

        analysis = DeltaAnalysis()

        if baseline_scan_id:
            # Compare assets
            await self._compare_assets(program_id, current_scan_id, baseline_scan_id, analysis)
            # Compare endpoints
            await self._compare_endpoints(program_id, current_scan_id, baseline_scan_id, analysis)
            # Compare findings
            await self._compare_findings(program_id, current_scan_id, baseline_scan_id, analysis)
        else:
            # First scan - all assets/findings are new
            await self._mark_all_as_new(program_id, current_scan_id, analysis)

        # Calculate summary
        analysis.summary = {
            "new_assets_count": len(analysis.new_assets),
            "removed_assets_count": len(analysis.removed_assets),
            "new_endpoints_count": len(analysis.new_endpoints),
            "removed_endpoints_count": len(analysis.removed_endpoints),
            "new_findings_count": len(analysis.new_findings),
            "removed_findings_count": len(analysis.removed_findings),
            "critical_findings_count": len(analysis.critical_findings),
            "has_significant_changes": self._is_significant(analysis),
        }

        return analysis

    async def _get_previous_completed_scan(
        self,
        program_id: UUID,
        exclude_scan_id: UUID,
    ) -> Optional[UUID]:
        """Get the most recent completed scan before the given one."""
        result = await self.db.execute(
            select(Scan).where(
                and_(
                    Scan.program_id == program_id,
                    Scan.status == ScanStatus.completed,
                    Scan.id != exclude_scan_id,
                    Scan.completed_at.isnot(None),
                )
            ).order_by(desc(Scan.completed_at)).limit(1)
        )
        previous_scan = result.scalars().first()
        return previous_scan.id if previous_scan else None

    async def _compare_assets(
        self,
        program_id: UUID,
        current_scan_id: UUID,
        baseline_scan_id: UUID,
        analysis: DeltaAnalysis,
    ) -> None:
        """Compare assets between two scans."""
        # Get current assets
        result = await self.db.execute(
            select(Asset).where(Asset.program_id == program_id)
        )
        current_assets = result.scalars().all()
        current_hostnames = {a.hostname for a in current_assets}

        # Compare with baseline to detect new/removed
        # Note: This is simplified - in production you'd track per-scan
        for asset in current_assets:
            # Check if asset is marked as newly discovered
            # (In full implementation, track discovery scan per asset)
            analysis.new_assets.append({
                "hostname": asset.hostname,
                "ip_address": asset.ip_address,
                "risk_score": asset.risk_score,
                "discovered_at": asset.first_seen,
            })

    async def _compare_endpoints(
        self,
        program_id: UUID,
        current_scan_id: UUID,
        baseline_scan_id: UUID,
        analysis: DeltaAnalysis,
    ) -> None:
        """Compare endpoints between two scans."""
        # Get assets for this program
        result = await self.db.execute(
            select(Asset).where(Asset.program_id == program_id)
        )
        assets = result.scalars().all()
        asset_ids = [a.id for a in assets]

        if not asset_ids:
            return

        # Get current endpoints
        result = await self.db.execute(
            select(Endpoint).where(Endpoint.asset_id.in_(asset_ids))
        )
        current_endpoints = result.scalars().all()

        for endpoint in current_endpoints:
            analysis.new_endpoints.append({
                "endpoint": endpoint.endpoint,
                "port": endpoint.port,
                "protocol": endpoint.protocol,
                "status": endpoint.status,
                "discovered_at": endpoint.discovered_at,
            })

    async def _compare_findings(
        self,
        program_id: UUID,
        current_scan_id: UUID,
        baseline_scan_id: UUID,
        analysis: DeltaAnalysis,
    ) -> None:
        """Compare findings between two scans."""
        # Get findings from current scan
        result = await self.db.execute(
            select(Finding).where(
                and_(
                    Finding.program_id == program_id,
                    Finding.scan_id == current_scan_id,
                )
            )
        )
        current_findings = result.scalars().all()

        for finding in current_findings:
            finding_dict = {
                "finding_id": finding.id,
                "title": finding.title,
                "severity": finding.severity,
                "endpoint": finding.endpoint,
                "description": finding.description,
                "discovered_at": finding.created_at,
            }

            analysis.new_findings.append(finding_dict)

            # Track critical findings
            if finding.severity == SeverityLevel.CRITICAL:
                analysis.critical_findings.append(finding_dict)

    async def _mark_all_as_new(
        self,
        program_id: UUID,
        current_scan_id: UUID,
        analysis: DeltaAnalysis,
    ) -> None:
        """Mark all assets/findings in initial scan as new."""
        # Mark all assets as new
        result = await self.db.execute(
            select(Asset).where(Asset.program_id == program_id)
        )
        assets = result.scalars().all()

        for asset in assets:
            analysis.new_assets.append({
                "hostname": asset.hostname,
                "ip_address": asset.ip_address,
                "risk_score": asset.risk_score,
                "discovered_at": asset.first_seen,
            })

        # Mark all endpoints as new
        asset_ids = [a.id for a in assets]
        if asset_ids:
            result = await self.db.execute(
                select(Endpoint).where(Endpoint.asset_id.in_(asset_ids))
            )
            endpoints = result.scalars().all()

            for endpoint in endpoints:
                analysis.new_endpoints.append({
                    "endpoint": endpoint.endpoint,
                    "port": endpoint.port,
                    "protocol": endpoint.protocol,
                    "status": endpoint.status,
                    "discovered_at": endpoint.discovered_at,
                })

        # Mark all findings as new
        result = await self.db.execute(
            select(Finding).where(
                and_(
                    Finding.program_id == program_id,
                    Finding.scan_id == current_scan_id,
                )
            )
        )
        findings = result.scalars().all()

        for finding in findings:
            finding_dict = {
                "finding_id": finding.id,
                "title": finding.title,
                "severity": finding.severity,
                "endpoint": finding.endpoint,
                "description": finding.description,
                "discovered_at": finding.created_at,
            }
            analysis.new_findings.append(finding_dict)

            if finding.severity == SeverityLevel.CRITICAL:
                analysis.critical_findings.append(finding_dict)

    def _is_significant(self, analysis: DeltaAnalysis) -> bool:
        """Determine if delta analysis indicates significant changes."""
        # Significant if:
        # - New critical findings detected
        # - More than 5 new high/critical findings
        # - More than 10 new assets
        # - More than 10 new endpoints

        if len(analysis.critical_findings) > 0:
            return True

        high_critical_count = len([
            f for f in analysis.new_findings
            if f.get("severity") in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        ])
        if high_critical_count >= 5:
            return True

        if len(analysis.new_assets) >= 10:
            return True

        if len(analysis.new_endpoints) >= 10:
            return True

        return False

    async def compare_asset_discovery(
        self,
        program_id: UUID,
        asset_hostname: str,
    ) -> dict:
        """Compare discovery history for a specific asset."""
        result = await self.db.execute(
            select(Asset).where(
                and_(
                    Asset.program_id == program_id,
                    Asset.hostname == asset_hostname,
                )
            )
        )
        asset = result.scalars().first()

        if not asset:
            return {"status": "asset_not_found"}

        return {
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "first_discovered": asset.first_seen,
            "last_seen": asset.last_seen,
            "is_alive": asset.is_alive,
            "risk_score": asset.risk_score,
            "discovery_history": {
                "first_discovery": asset.first_seen.isoformat() if asset.first_seen else None,
                "last_activity": asset.last_seen.isoformat() if asset.last_seen else None,
                "days_monitored": (asset.last_seen - asset.first_seen).days if asset.first_seen and asset.last_seen else 0,
            },
        }

    async def get_asset_timeline(
        self,
        program_id: UUID,
        asset_hostname: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get discovery timeline for an asset."""
        result = await self.db.execute(
            select(Asset).where(
                and_(
                    Asset.program_id == program_id,
                    Asset.hostname == asset_hostname,
                )
            )
        )
        asset = result.scalars().first()

        if not asset:
            return []

        # Get endpoint history for asset
        result = await self.db.execute(
            select(Endpoint)
            .where(Endpoint.asset_id == asset.id)
            .order_by(desc(Endpoint.discovered_at))
            .limit(limit)
        )
        endpoints = result.scalars().all()

        return [
            {
                "event_type": "endpoint_discovery",
                "endpoint": ep.endpoint,
                "port": ep.port,
                "protocol": ep.protocol,
                "discovered_at": ep.discovered_at.isoformat() if ep.discovered_at else None,
            }
            for ep in endpoints
        ]
