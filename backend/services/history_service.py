"""
Service layer for historical intelligence orchestration.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.history.context_recall import ContextRecall
from backend.ai.history.hunt_memory_engine import HuntMemoryEngine
from backend.ai.history.memory_summarizer import (
    compress_historical_context,
    summarize_hunt_history,
    summarize_recurring_risks,
)
from backend.intelligence.history.exposure_history import ExposureHistory
from backend.intelligence.history.findings_history import FindingsHistory
from backend.intelligence.history.risk_history import RiskHistory


class HistoryService:
    """Orchestrates memory, findings, exposure, and risk history."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_engine = HuntMemoryEngine(db)
        self.context_recall = ContextRecall(db)
        self.risk_history = RiskHistory(db)
        self.exposure_history = ExposureHistory(db)
        self.findings_history = FindingsHistory(db)

    async def retrieve_historical_context(
        self,
        organization_id: UUID,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        similar_findings = await self.context_recall.recall_similar_findings(organization_id, query, limit=limit)
        attack_paths = await self.context_recall.recall_attack_paths(organization_id, query, limit=limit)
        exposure = await self.context_recall.recall_historical_exposure(organization_id, query, limit=limit)
        memories = await self.memory_engine.retrieve_related_memory(organization_id, query, limit=limit)

        compressed_context = compress_historical_context(
            [
                *memories,
                *similar_findings,
                *attack_paths,
                *exposure,
            ]
        )

        return {
            "organization_id": str(organization_id),
            "query": query,
            "similar_findings": similar_findings,
            "attack_paths": attack_paths,
            "historical_exposure": exposure,
            "related_memory": memories,
            "compressed_context": compressed_context,
        }

    async def generate_history_summary(
        self,
        organization_id: UUID,
        limit: int = 20,
    ) -> dict[str, Any]:
        memory_summary = await self.memory_engine.summarize_historical_patterns(organization_id, limit=limit)
        finding_summary = await self.findings_history.track_recurring_findings(organization_id, limit=limit)
        exposure_summary = await self.exposure_history.detect_exposure_patterns(organization_id, limit=limit)
        risk_summary = await self.risk_history.analyze_risk_trends(organization_id, limit=limit)

        return {
            "organization_id": str(organization_id),
            "memory": memory_summary,
            "findings": finding_summary,
            "exposure": exposure_summary,
            "risk": risk_summary,
            "compressed_risk_context": summarize_recurring_risks(risk_summary.get("snapshots", [])),
            "compressed_memory_context": summarize_hunt_history(memory_summary.get("recent_memories", [])),
        }

    async def analyze_org_risk_evolution(
        self,
        organization_id: UUID,
        limit: int = 20,
    ) -> dict[str, Any]:
        risk_trends = await self.risk_history.analyze_risk_trends(organization_id, limit=limit)
        exposure_patterns = await self.exposure_history.detect_exposure_patterns(organization_id, limit=limit)
        recurring_findings = await self.findings_history.track_recurring_findings(organization_id, limit=limit)

        return {
            "organization_id": str(organization_id),
            "risk_trends": risk_trends,
            "exposure_patterns": exposure_patterns,
            "recurring_findings": recurring_findings,
        }

