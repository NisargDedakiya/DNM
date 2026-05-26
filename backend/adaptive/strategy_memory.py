"""
Strategy memory utilities for learned hunt patterns.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.strategy_memory import StrategyMemory


class StrategyMemoryStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def store_strategy_pattern(self, organization_id: UUID, methodology_pattern: dict[str, Any], success_score: float) -> StrategyMemory:
        memory = StrategyMemory(
            organization_id=organization_id,
            methodology_pattern=methodology_pattern,
            success_score=float(success_score),
        )
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        return memory

    async def retrieve_successful_patterns(self, organization_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(StrategyMemory)
            .where(StrategyMemory.organization_id == organization_id)
            .order_by(StrategyMemory.success_score.desc(), StrategyMemory.created_at.desc())
            .limit(limit),
        )
        memories = result.scalars().all()
        return [
            {
                "id": memory.id,
                "methodology_pattern": memory.methodology_pattern or {},
                "success_score": memory.success_score,
                "created_at": memory.created_at,
            }
            for memory in memories
        ]

    async def evolve_historical_methodologies(self, organization_id: UUID) -> dict[str, Any]:
        patterns = await self.retrieve_successful_patterns(organization_id, limit=20)
        if not patterns:
            return {"organization_id": str(organization_id), "patterns": [], "insight": "No historical strategy memory yet."}
        average_success = round(sum(float(pattern["success_score"]) for pattern in patterns) / len(patterns), 2)
        focus_counts: dict[str, int] = {}
        for pattern in patterns:
            focus_areas = pattern.get("methodology_pattern", {}).get("strategy_context", {}).get("focus_areas", [])
            for focus in focus_areas:
                focus_counts[focus] = focus_counts.get(focus, 0) + 1
        return {
            "organization_id": str(organization_id),
            "average_success_score": average_success,
            "focus_area_trends": sorted(focus_counts.items(), key=lambda item: item[1], reverse=True),
            "patterns": patterns,
        }
