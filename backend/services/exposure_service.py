"""
Exposure intelligence service.
Manages exposure lifecycle, tracking, and categorization.
"""
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.exposure import (
    Exposure,
    ExposureHistory,
    ExposureType,
    RiskLevel,
)
from backend.models.asset import Asset
from backend.models.finding import Finding


class ExposureService:
    """
    Manages exposure lifecycle, tracking, and analysis.
    Integrates fingerprinting into exposure discovery.
    """

    def __init__(self, db: AsyncSession):
        """Initialize exposure service."""
        self.db = db

    async def create_exposure(
        self,
        asset_id: UUID,
        organization_id: UUID,
        exposure_type: str,
        title: str,
        description: str,
        risk_level: str,
        confidence_score: float = 0.8,
        fingerprint_data: Optional[dict] = None,
        evidence: Optional[dict] = None,
        finding_id: Optional[UUID] = None,
    ) -> Exposure:
        """
        Create new exposure record.

        Args:
            asset_id: Asset with exposure
            organization_id: Organization context
            exposure_type: Type of exposure
            title: Short title
            description: Detailed description
            risk_level: Risk classification
            confidence_score: Detection confidence (0-1)
            fingerprint_data: Technology fingerprint details
            evidence: Detection evidence
            finding_id: Linked finding (optional)

        Returns:
            Exposure: Created exposure record
        """
        now = datetime.utcnow()

        exposure = Exposure(
            asset_id=asset_id,
            organization_id=organization_id,
            finding_id=finding_id,
            exposure_type=exposure_type,
            title=title,
            description=description,
            risk_level=risk_level,
            confidence_score=confidence_score,
            fingerprint_data=fingerprint_data or {},
            evidence=evidence or {},
            first_detected=now,
            last_detected=now,
            detection_count=1,
        )

        self.db.add(exposure)
        await self.db.flush()

        # Record creation in history
        await self._record_history(
            exposure_id=exposure.id,
            asset_id=asset_id,
            organization_id=organization_id,
            change_type="created",
            new_state={
                "type": exposure_type,
                "risk_level": risk_level,
            },
        )

        return exposure

    async def update_exposure(
        self,
        exposure_id: UUID,
        risk_level: Optional[str] = None,
        confidence_score: Optional[float] = None,
        is_active: Optional[bool] = None,
        remediation_status: Optional[str] = None,
        remediation_notes: Optional[str] = None,
    ) -> Exposure:
        """
        Update exposure record.

        Args:
            exposure_id: Exposure ID
            risk_level: New risk level
            confidence_score: New confidence
            is_active: Active status
            remediation_status: Remediation progress
            remediation_notes: Remediation notes

        Returns:
            Exposure: Updated exposure
        """
        exposure = await self.get_exposure(exposure_id)
        if not exposure:
            raise ValueError(f"Exposure {exposure_id} not found")

        # Track previous state
        previous_state = {
            "risk_level": exposure.risk_level,
            "confidence_score": exposure.confidence_score,
            "is_active": exposure.is_active,
        }

        # Update fields
        if risk_level is not None:
            exposure.risk_level = risk_level
        if confidence_score is not None:
            exposure.confidence_score = confidence_score
        if is_active is not None:
            exposure.is_active = is_active
        if remediation_status is not None:
            exposure.remediation_status = remediation_status
        if remediation_notes is not None:
            exposure.remediation_notes = remediation_notes

        exposure.updated_at = datetime.utcnow()
        await self.db.flush()

        # Record update in history
        await self._record_history(
            exposure_id=exposure_id,
            asset_id=exposure.asset_id,
            organization_id=exposure.organization_id,
            change_type="updated",
            previous_state=previous_state,
            new_state={
                "risk_level": exposure.risk_level,
                "is_active": exposure.is_active,
            },
        )

        return exposure

    async def redetect_exposure(
        self,
        exposure_id: UUID,
        new_evidence: Optional[dict] = None,
    ) -> Exposure:
        """
        Mark exposure as re-detected in new scan.

        Args:
            exposure_id: Exposure ID
            new_evidence: Updated evidence from detection

        Returns:
            Exposure: Updated exposure
        """
        exposure = await self.get_exposure(exposure_id)
        if not exposure:
            raise ValueError(f"Exposure {exposure_id} not found")

        now = datetime.utcnow()

        exposure.last_detected = now
        exposure.detection_count += 1
        exposure.is_active = True

        if new_evidence:
            exposure.evidence = new_evidence

        await self.db.flush()

        # Record redetection
        await self._record_history(
            exposure_id=exposure_id,
            asset_id=exposure.asset_id,
            organization_id=exposure.organization_id,
            change_type="redetected",
            new_state={
                "last_detected": now.isoformat(),
                "detection_count": exposure.detection_count,
            },
        )

        return exposure

    async def resolve_exposure(
        self,
        exposure_id: UUID,
        remediation_status: str,
        notes: str,
    ) -> Exposure:
        """
        Mark exposure as resolved.

        Args:
            exposure_id: Exposure ID
            remediation_status: Resolution status
            notes: Remediation notes

        Returns:
            Exposure: Updated exposure
        """
        exposure = await self.get_exposure(exposure_id)
        if not exposure:
            raise ValueError(f"Exposure {exposure_id} not found")

        exposure.is_active = False
        exposure.remediation_status = remediation_status
        exposure.remediation_notes = notes
        exposure.updated_at = datetime.utcnow()

        await self.db.flush()

        # Record resolution
        await self._record_history(
            exposure_id=exposure_id,
            asset_id=exposure.asset_id,
            organization_id=exposure.organization_id,
            change_type="remediated",
            new_state={
                "remediation_status": remediation_status,
                "is_active": False,
            },
            change_reason=notes,
        )

        return exposure

    async def get_exposure(self, exposure_id: UUID) -> Optional[Exposure]:
        """Get exposure by ID."""
        result = await self.db.execute(
            select(Exposure).where(Exposure.id == exposure_id)
        )
        return result.scalars().first()

    async def get_asset_exposures(
        self,
        asset_id: UUID,
        active_only: bool = True,
        risk_level: Optional[str] = None,
    ) -> list[Exposure]:
        """
        Get exposures for asset.

        Args:
            asset_id: Asset ID
            active_only: Only active exposures
            risk_level: Filter by risk level

        Returns:
            list[Exposure]: Asset exposures
        """
        query = select(Exposure).where(Exposure.asset_id == asset_id)

        if active_only:
            query = query.where(Exposure.is_active == True)

        if risk_level:
            query = query.where(Exposure.risk_level == risk_level)

        result = await self.db.execute(
            query.order_by(Exposure.risk_score.desc())
        )
        return result.scalars().all()

    async def get_organization_exposures(
        self,
        organization_id: UUID,
        active_only: bool = True,
        risk_level: Optional[str] = None,
        exposure_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[Exposure]:
        """
        Get exposures for organization.

        Args:
            organization_id: Organization ID
            active_only: Only active exposures
            risk_level: Filter by risk level
            exposure_type: Filter by type
            limit: Result limit

        Returns:
            list[Exposure]: Organization exposures
        """
        query = select(Exposure).where(Exposure.organization_id == organization_id)

        if active_only:
            query = query.where(Exposure.is_active == True)

        if risk_level:
            query = query.where(Exposure.risk_level == risk_level)

        if exposure_type:
            query = query.where(Exposure.exposure_type == exposure_type)

        result = await self.db.execute(
            query.order_by(Exposure.risk_score.desc()).limit(limit)
        )
        return result.scalars().all()

    async def get_exposure_history(
        self,
        exposure_id: UUID,
        limit: int = 50,
    ) -> list[ExposureHistory]:
        """Get change history for exposure."""
        result = await self.db.execute(
            select(ExposureHistory)
            .where(ExposureHistory.exposure_id == exposure_id)
            .order_by(ExposureHistory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def categorize_exposure(
        self,
        exposure_type: str,
        fingerprint_data: Optional[dict] = None,
        status_code: Optional[int] = None,
    ) -> dict:
        """
        Categorize exposure and provide remediation guidance.

        Args:
            exposure_type: Type of exposure
            fingerprint_data: Technology fingerprint
            status_code: HTTP status code

        Returns:
            dict: {
                category, severity, remediation_priority,
                suggested_actions: [], attack_vectors: []
            }
        """
        categorization = {
            "category": "misconfiguration",
            "severity": "medium",
            "remediation_priority": 3,
            "suggested_actions": [],
            "attack_vectors": [],
        }

        if exposure_type == "public_admin_panel":
            categorization.update(
                {
                    "category": "exposed_interface",
                    "severity": "critical",
                    "remediation_priority": 1,
                    "attack_vectors": [
                        "Unauthorized access",
                        "Account takeover",
                        "Data modification",
                    ],
                    "suggested_actions": [
                        "Require authentication for admin panel",
                        "Implement rate limiting",
                        "Restrict by IP range",
                        "Enable MFA",
                    ],
                }
            )

        elif exposure_type == "exposed_api":
            categorization.update(
                {
                    "category": "api_exposure",
                    "severity": "critical",
                    "remediation_priority": 1,
                    "attack_vectors": [
                        "Unauthorized data access",
                        "Data exfiltration",
                        "API manipulation",
                    ],
                    "suggested_actions": [
                        "Implement API authentication",
                        "Add rate limiting",
                        "Validate all inputs",
                        "Log all access",
                    ],
                }
            )

        elif exposure_type == "outdated_technology":
            categorization.update(
                {
                    "category": "software_vulnerability",
                    "severity": "high",
                    "remediation_priority": 2,
                    "attack_vectors": [
                        "Known CVE exploitation",
                        "Remote code execution",
                        "Information disclosure",
                    ],
                    "suggested_actions": [
                        "Update to latest version",
                        "Apply security patches",
                        "Monitor for CVEs",
                        "Consider replacement",
                    ],
                }
            )

        elif exposure_type == "weak_headers":
            categorization.update(
                {
                    "category": "security_misconfiguration",
                    "severity": "medium",
                    "remediation_priority": 3,
                    "attack_vectors": [
                        "XSS attacks",
                        "Clickjacking",
                        "Man-in-the-middle",
                    ],
                    "suggested_actions": [
                        "Add CSP header",
                        "Enable HSTS",
                        "Add X-Frame-Options",
                        "Review security headers",
                    ],
                }
            )

        elif exposure_type == "exposed_storage":
            categorization.update(
                {
                    "category": "data_exposure",
                    "severity": "critical",
                    "remediation_priority": 1,
                    "attack_vectors": [
                        "Data theft",
                        "Privacy breach",
                        "Compliance violation",
                    ],
                    "suggested_actions": [
                        "Restrict public access",
                        "Enable authentication",
                        "Encrypt data",
                        "Audit permissions",
                    ],
                }
            )

        elif exposure_type == "debug_interface":
            categorization.update(
                {
                    "category": "information_disclosure",
                    "severity": "high",
                    "remediation_priority": 2,
                    "attack_vectors": [
                        "Source code disclosure",
                        "Configuration exposure",
                        "Internal path leakage",
                    ],
                    "suggested_actions": [
                        "Disable debug mode",
                        "Remove debug endpoints",
                        "Sanitize error messages",
                        "Use production config",
                    ],
                }
            )

        return categorization

    async def _record_history(
        self,
        exposure_id: UUID,
        asset_id: UUID,
        organization_id: UUID,
        change_type: str,
        new_state: Optional[dict] = None,
        previous_state: Optional[dict] = None,
        change_reason: Optional[str] = None,
    ) -> ExposureHistory:
        """Record exposure change in history."""
        history = ExposureHistory(
            exposure_id=exposure_id,
            asset_id=asset_id,
            organization_id=organization_id,
            change_type=change_type,
            new_state=new_state,
            previous_state=previous_state,
            change_reason=change_reason,
        )

        self.db.add(history)
        await self.db.flush()

        return history

    async def track_exposure_changes(
        self,
        organization_id: UUID,
        since: Optional[datetime] = None,
    ) -> dict:
        """
        Get exposure change summary.

        Args:
            organization_id: Organization ID
            since: Track changes since time

        Returns:
            dict: {
                total_created, total_resolved, total_redetected,
                by_type: {}, by_risk_level: {}
            }
        """
        if not since:
            since = datetime.utcnow() - timedelta(days=7)

        result = await self.db.execute(
            select(ExposureHistory).where(
                and_(
                    ExposureHistory.organization_id == organization_id,
                    ExposureHistory.created_at >= since,
                )
            )
        )
        changes = result.scalars().all()

        summary = {
            "total_created": sum(
                1 for c in changes if c.change_type == "created"
            ),
            "total_resolved": sum(
                1 for c in changes if c.change_type == "remediated"
            ),
            "total_redetected": sum(
                1 for c in changes if c.change_type == "redetected"
            ),
            "by_type": {},
            "by_risk_level": {},
        }

        return summary
