"""
Track risk evolution and escalating exposure states over time.
"""
from __future__ import annotations

from statistics import mean
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.exposure_snapshot import ExposureSnapshot
from backend.models.risk_evolution_event import RiskEvolutionEvent


class RiskEvolution:
    """Risk trend and escalation analysis for exposure history."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def calculate_risk_evolution(
        self,
        previous_risk: float,
        current_risk: float,
    ) -> dict[str, Any]:
        delta = round(float(current_risk) - float(previous_risk), 2)
        if delta >= 3:
            direction = "escalating"
        elif delta <= -3:
            direction = "improving"
        else:
            direction = "stable"
        return {
            "previous_risk": round(float(previous_risk), 2),
            "current_risk": round(float(current_risk), 2),
            "delta": delta,
            "direction": direction,
        }

    def identify_risk_escalation(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [item for item in history if float(item.get("delta", 0.0)) > 0.0]

    async def generate_risk_history(
        self,
        organization_id: UUID,
        asset: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = select(RiskEvolutionEvent).where(RiskEvolutionEvent.organization_id == organization_id)
        if asset:
            query = query.where(RiskEvolutionEvent.asset == asset)
        query = query.order_by(desc(RiskEvolutionEvent.created_at)).limit(limit)
        result = await self.db.execute(query)
        events = result.scalars().all()

        return [
            {
                "id": str(event.id),
                "organization_id": str(event.organization_id),
                "asset": event.asset,
                "previous_risk": round(float(event.previous_risk), 2),
                "current_risk": round(float(event.current_risk), 2),
                "delta": round(float(event.current_risk) - float(event.previous_risk), 2),
                "summary": event.summary,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]

    async def record_risk_evolution(
        self,
        organization_id: UUID,
        asset: str,
        previous_risk: float,
        current_risk: float,
        summary: str,
    ) -> RiskEvolutionEvent:
        event = RiskEvolutionEvent(
            organization_id=organization_id,
            asset=asset,
            previous_risk=previous_risk,
            current_risk=current_risk,
            summary=summary,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def summarize_history(self, organization_id: UUID, asset: str | None = None, limit: int = 20) -> dict[str, Any]:
        history = await self.generate_risk_history(organization_id, asset=asset, limit=limit)
        scores = [item["current_risk"] for item in history]
        return {
            "organization_id": str(organization_id),
            "asset": asset,
            "history": history,
            "average_risk": round(mean(scores), 2) if scores else 0.0,
            "latest_risk": scores[0] if scores else 0.0,
            "escalations": self.identify_risk_escalation(history),
        }

