"""
Risk scoring service.
Calculates asset criticality, exposure prioritization, and attack surface risk.
"""
from uuid import UUID
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.exposure import Exposure, RiskLevel
from backend.models.asset import Asset
from backend.models.finding import Finding


class RiskService:
    """
    Comprehensive risk scoring and prioritization engine.
    Calculates criticality, exposure scores, and attack surface risk.
    """

    # Risk level weights
    RISK_WEIGHTS = {
        "critical": 10.0,
        "high": 7.5,
        "medium": 5.0,
        "low": 2.5,
        "info": 1.0,
    }

    # Exposure type criticality multipliers
    EXPOSURE_CRITICALITY = {
        "public_admin_panel": 1.5,
        "exposed_api": 1.4,
        "database_exposure": 1.5,
        "outdated_technology": 1.2,
        "weak_headers": 0.8,
        "exposed_storage": 1.4,
        "debug_interface": 1.1,
        "weak_authentication": 1.3,
        "service_misconfiguration": 1.0,
        "information_disclosure": 0.9,
        "unpatched_service": 1.2,
        "certificate_issue": 0.9,
    }

    # Asset criticality factors
    ASSET_CRITICALITY_FACTORS = {
        "internet_facing": 1.5,  # Directly accessible
        "has_api": 1.3,  # API exposure risk
        "has_admin_panel": 1.4,  # Admin access
        "stores_sensitive_data": 1.6,  # Data criticality
        "authentication_required": 0.7,  # Protected
        "internal_only": 0.5,  # Internal network
    }

    def __init__(self, db: AsyncSession):
        """Initialize risk service."""
        self.db = db

    async def calculate_asset_risk(
        self,
        asset_id: UUID,
    ) -> dict:
        """
        Calculate overall risk score for asset.

        Args:
            asset_id: Asset ID

        Returns:
            dict: {
                asset_id, overall_risk_score, risk_level,
                exposures_count, critical_exposures,
                asset_criticality, factors: {}
            }
        """
        # Get asset exposures
        result = await self.db.execute(
            select(Exposure)
            .where(and_(
                Exposure.asset_id == asset_id,
                Exposure.is_active == True,
            ))
            .order_by(Exposure.risk_score.desc())
        )
        exposures = result.scalars().all()

        # Calculate base risk from exposures
        exposure_score = 0.0
        critical_count = 0
        high_count = 0

        for exposure in exposures:
            # Base risk weight
            base_weight = self.RISK_WEIGHTS.get(
                exposure.risk_level, 5.0
            )

            # Apply exposure type criticality
            criticality_mult = self.EXPOSURE_CRITICALITY.get(
                exposure.exposure_type, 1.0
            )

            # Apply confidence
            exposure_risk = (
                base_weight
                * criticality_mult
                * exposure.confidence_score
            )

            exposure_score += exposure_risk

            if exposure.risk_level == "critical":
                critical_count += 1
            elif exposure.risk_level == "high":
                high_count += 1

        # Apply asset criticality multiplier
        asset_criticality = await self._calculate_asset_criticality(asset_id)
        overall_score = exposure_score * asset_criticality

        # Normalize to 0-100 scale
        normalized_score = min(100.0, overall_score)

        # Determine risk level
        risk_level = self._score_to_risk_level(normalized_score)

        return {
            "asset_id": str(asset_id),
            "overall_risk_score": round(normalized_score, 2),
            "risk_level": risk_level,
            "exposures_count": len(exposures),
            "critical_exposures": critical_count,
            "high_exposures": high_count,
            "asset_criticality": round(asset_criticality, 2),
            "factors": {
                "exposure_score": round(exposure_score, 2),
                "criticality_multiplier": round(asset_criticality, 2),
                "normalized_score": round(normalized_score, 2),
            },
        }

    async def calculate_exposure_score(
        self,
        exposure_id: UUID,
    ) -> float:
        """
        Calculate risk score for single exposure.

        Args:
            exposure_id: Exposure ID

        Returns:
            float: Risk score (0-100)
        """
        result = await self.db.execute(
            select(Exposure).where(Exposure.id == exposure_id)
        )
        exposure = result.scalars().first()

        if not exposure:
            return 0.0

        # Base weight from risk level
        base_weight = self.RISK_WEIGHTS.get(exposure.risk_level, 5.0)

        # Type criticality
        criticality_mult = self.EXPOSURE_CRITICALITY.get(
            exposure.exposure_type, 1.0
        )

        # Confidence factor
        confidence = exposure.confidence_score

        # Detection recency (recent detections more critical)
        recency_factor = 1.0
        if exposure.detection_count > 1:
            recency_factor = 1.2  # Multiple detections

        # Calculate score
        score = (
            base_weight
            * criticality_mult
            * confidence
            * recency_factor
            * exposure.criticality_factor
        )

        # Normalize to 0-100
        normalized = min(100.0, score)

        # Update exposure record
        exposure.risk_score = normalized
        await self.db.flush()

        return normalized

    async def rank_exposures(
        self,
        organization_id: UUID,
        active_only: bool = True,
        limit: int = 50,
    ) -> list[dict]:
        """
        Rank exposures by risk priority.

        Args:
            organization_id: Organization ID
            active_only: Only active exposures
            limit: Result limit

        Returns:
            list[dict]: Ranked exposures with risk info
        """
        query = select(Exposure).where(
            Exposure.organization_id == organization_id
        )

        if active_only:
            query = query.where(Exposure.is_active == True)

        result = await self.db.execute(
            query.order_by(Exposure.risk_score.desc()).limit(limit)
        )
        exposures = result.scalars().all()

        ranked = []
        for rank, exposure in enumerate(exposures, 1):
            ranked.append(
                {
                    "rank": rank,
                    "exposure_id": str(exposure.id),
                    "asset_id": str(exposure.asset_id),
                    "type": exposure.exposure_type,
                    "risk_level": exposure.risk_level,
                    "risk_score": round(exposure.risk_score, 2),
                    "title": exposure.title,
                    "confidence": round(exposure.confidence_score, 2),
                    "detected_days_ago": (
                        (
                            exposure.last_detected
                            - exposure.first_detected
                        ).days
                    ),
                    "detection_count": exposure.detection_count,
                }
            )

        return ranked

    async def calculate_attack_surface_score(
        self,
        organization_id: UUID,
    ) -> dict:
        """
        Calculate overall attack surface risk score.

        Args:
            organization_id: Organization ID

        Returns:
            dict: {
                overall_score, risk_level, asset_count,
                exposed_assets, critical_count, exposure_distribution
            }
        """
        # Get all active exposures
        result = await self.db.execute(
            select(Exposure).where(
                and_(
                    Exposure.organization_id == organization_id,
                    Exposure.is_active == True,
                )
            )
        )
        exposures = result.scalars().all()

        if not exposures:
            return {
                "overall_score": 0.0,
                "risk_level": "low",
                "asset_count": 0,
                "exposed_assets": 0,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "exposure_distribution": {},
            }

        # Count exposed assets
        exposed_asset_ids = set(e.asset_id for e in exposures)

        # Calculate aggregate score
        aggregate_score = sum(e.risk_score for e in exposures) / len(
            exposures
        )

        # Count by severity
        critical_count = sum(
            1 for e in exposures if e.risk_level == "critical"
        )
        high_count = sum(
            1 for e in exposures if e.risk_level == "high"
        )
        medium_count = sum(
            1 for e in exposures if e.risk_level == "medium"
        )

        # Distribution by type
        distribution = {}
        for exposure in exposures:
            exposure_type = exposure.exposure_type
            if exposure_type not in distribution:
                distribution[exposure_type] = 0
            distribution[exposure_type] += 1

        # Determine overall risk level
        overall_level = self._score_to_risk_level(aggregate_score)

        return {
            "overall_score": round(aggregate_score, 2),
            "risk_level": overall_level,
            "total_exposures": len(exposures),
            "exposed_assets": len(exposed_asset_ids),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "exposure_distribution": distribution,
            "top_exposure_types": sorted(
                distribution.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5],
        }

    async def get_risk_heatmap(
        self,
        organization_id: UUID,
    ) -> dict:
        """
        Generate risk heatmap data for visualization.

        Args:
            organization_id: Organization ID

        Returns:
            dict: {
                by_risk_level, by_asset, by_exposure_type,
                critical_timeline, trend
            }
        """
        result = await self.db.execute(
            select(Exposure).where(
                Exposure.organization_id == organization_id
            )
        )
        all_exposures = result.scalars().all()

        # Group by risk level
        by_risk_level = {}
        for level in ["critical", "high", "medium", "low", "info"]:
            by_risk_level[level] = sum(
                1 for e in all_exposures if e.risk_level == level
            )

        # Group by exposure type
        by_type = {}
        for exposure in all_exposures:
            exp_type = exposure.exposure_type
            if exp_type not in by_type:
                by_type[exp_type] = 0
            by_type[exp_type] += 1

        # Get critical assets (by exposure count)
        asset_exposure_count = {}
        for exposure in all_exposures:
            if exposure.is_active:
                asset_id = str(exposure.asset_id)
                if asset_id not in asset_exposure_count:
                    asset_exposure_count[asset_id] = 0
                asset_exposure_count[asset_id] += 1

        # Top critical assets
        critical_assets = sorted(
            asset_exposure_count.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "by_risk_level": by_risk_level,
            "by_exposure_type": by_type,
            "critical_assets": [
                {
                    "asset_id": asset_id,
                    "exposure_count": count,
                }
                for asset_id, count in critical_assets
            ],
            "total_exposures": len(all_exposures),
            "unique_assets_affected": len(set(
                e.asset_id for e in all_exposures
            )),
        }

    async def _calculate_asset_criticality(self, asset_id: UUID) -> float:
        """
        Calculate criticality multiplier for asset.

        Args:
            asset_id: Asset ID

        Returns:
            float: Criticality multiplier (0.5-2.0)
        """
        result = await self.db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        asset = result.scalars().first()

        if not asset:
            return 1.0

        multiplier = 1.0

        # Internet-facing assets are more critical
        if asset.is_internet_facing:
            multiplier *= self.ASSET_CRITICALITY_FACTORS.get(
                "internet_facing", 1.0
            )

        # Apply minimum/maximum bounds
        return max(0.5, min(2.0, multiplier))

    @staticmethod
    def _score_to_risk_level(score: float) -> str:
        """Convert numeric score to risk level."""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        else:
            return "info"

    async def get_remediation_priorities(
        self,
        organization_id: UUID,
        limit: int = 20,
    ) -> list[dict]:
        """
        Get prioritized list of remediation tasks.

        Args:
            organization_id: Organization ID
            limit: Result limit

        Returns:
            list[dict]: Prioritized remediations
        """
        # Get highest-risk, unresolved exposures
        result = await self.db.execute(
            select(Exposure)
            .where(
                and_(
                    Exposure.organization_id == organization_id,
                    Exposure.is_active == True,
                    Exposure.remediation_status == None,
                )
            )
            .order_by(Exposure.risk_score.desc())
            .limit(limit)
        )
        exposures = result.scalars().all()

        priorities = []
        for exposure in exposures:
            priorities.append(
                {
                    "exposure_id": str(exposure.id),
                    "asset_id": str(exposure.asset_id),
                    "type": exposure.exposure_type,
                    "title": exposure.title,
                    "risk_score": round(exposure.risk_score, 2),
                    "confidence": round(exposure.confidence_score, 2),
                    "first_detected": exposure.first_detected.isoformat(),
                    "days_exposed": (
                        (
                            exposure.last_detected
                            - exposure.first_detected
                        ).days
                    ),
                }
            )

        return priorities
