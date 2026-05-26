"""
Recurring findings intelligence and historical correlation helpers.
"""
from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.history.hunt_memory_engine import HuntMemoryEngine
from backend.models.finding import Finding


class FindingsHistory:
    """Organization-isolated finding history and repeat detection."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_engine = HuntMemoryEngine(db)

    async def track_recurring_findings(
        self,
        organization_id: UUID,
        limit: int = 100,
    ) -> dict[str, Any]:
        finding_rows = await self._get_findings(organization_id, limit=limit)
        repeat_patterns = self.identify_repeat_patterns(finding_rows)
        correlated = await self.correlate_historical_findings(organization_id, limit=limit)

        return {
            "organization_id": str(organization_id),
            "total_findings": len(finding_rows),
            "repeat_patterns": repeat_patterns,
            "correlated_history": correlated,
        }

    async def correlate_historical_findings(
        self,
        organization_id: UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        finding_rows = await self._get_findings(organization_id, limit=limit)
        memory_rows = await self.memory_engine.retrieve_related_memory(
            organization_id=organization_id,
            query="finding recurring vulnerability attack chain",
            memory_type="findings",
            limit=limit,
        )

        return [
            {
                "finding": finding_rows[index] if index < len(finding_rows) else None,
                "memory": memory_rows[index] if index < len(memory_rows) else None,
            }
            for index in range(max(len(finding_rows), len(memory_rows)))
        ]

    def identify_repeat_patterns(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pattern_counts = Counter()
        pattern_examples: dict[str, dict[str, Any]] = {}

        for finding in findings:
            title = (finding.get("title") or "").strip().lower()
            severity = (finding.get("severity") or "unknown").strip().lower()
            endpoint = (finding.get("endpoint") or "").strip().lower()
            key = "|".join(part for part in (title, severity, endpoint[:80]) if part)
            if not key:
                continue
            pattern_counts[key] += 1
            pattern_examples.setdefault(key, finding)

        return [
            {
                "pattern": pattern,
                "count": count,
                "example": pattern_examples[pattern],
            }
            for pattern, count in pattern_counts.most_common()
            if count > 1
        ]

    async def _get_findings(self, organization_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
        stmt = (
            select(Finding)
            .where(Finding.organization_id == organization_id)
            .order_by(desc(Finding.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        findings = result.scalars().all()

        return [
            {
                "id": str(finding.id),
                "title": finding.title,
                "severity": str(finding.severity),
                "status": str(finding.status),
                "endpoint": finding.endpoint,
                "description": finding.description[:400],
                "created_at": finding.created_at.isoformat(),
            }
            for finding in findings
        ]

