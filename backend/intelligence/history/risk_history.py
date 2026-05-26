"""
Risk history intelligence for long-term risk evolution tracking.
"""
from __future__ import annotations

from statistics import mean
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.risk_snapshot import RiskSnapshot


class RiskHistory:
    """Organization-isolated risk history operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def track_risk_change(
        self,
        organization_id: UUID,
        risk_score: float,
        summary: str,
    ) -> RiskSnapshot:
        snapshot = RiskSnapshot(
            organization_id=organization_id,
            risk_score=max(0.0, float(risk_score)),
            summary=" ".join(summary.split())[:4000],
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def analyze_risk_trends(
        self,
        organization_id: UUID,
        limit: int = 20,
    ) -> dict[str, Any]:
        snapshots = await self.generate_risk_history(organization_id, limit=limit)
        scores = [item["risk_score"] for item in snapshots]

        trend = "stable"
        if len(scores) >= 2:
            delta = scores[0] - scores[-1]
            if delta > 0.5:
                trend = "worsening"
            elif delta < -0.5:
                trend = "improving"

        return {
            "organization_id": str(organization_id),
            "trend": trend,
            "latest_score": scores[0] if scores else 0.0,
            "average_score": round(mean(scores), 2) if scores else 0.0,
            "risk_delta": round((scores[0] - scores[-1]), 2) if len(scores) >= 2 else 0.0,
            "snapshots": snapshots,
        }

    async def generate_risk_history(
        self,
        organization_id: UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(RiskSnapshot)
            .where(RiskSnapshot.organization_id == organization_id)
            .order_by(desc(RiskSnapshot.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        snapshots = result.scalars().all()

        return [
            {
                "id": str(snapshot.id),
                "organization_id": str(snapshot.organization_id),
                "risk_score": round(float(snapshot.risk_score), 2),
                "summary": snapshot.summary,
                "created_at": snapshot.created_at.isoformat(),
            }
            for snapshot in snapshots
        ]

