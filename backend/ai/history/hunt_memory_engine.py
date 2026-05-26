"""
Organization-aware persistent hunt memory engine.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import cast, desc, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.hunt_memory import HuntMemory

logger = logging.getLogger(__name__)

ALLOWED_MEMORY_TYPES = {
    "findings",
    "attack_chain",
    "recon",
    "technology",
    "report",
}


def _normalize_memory_type(memory_type: str) -> str:
    normalized = (memory_type or "").strip().lower().replace("-", "_")
    return normalized if normalized in ALLOWED_MEMORY_TYPES else "findings"


def _sanitize_text(value: str) -> str:
    return " ".join((value or "").strip().split())[:4000]


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None

    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if key in {"evidence", "raw_evidence", "secrets", "credentials", "tokens"}:
            continue
        if isinstance(value, str):
            sanitized[key] = _sanitize_text(value)
        elif isinstance(value, (int, float, bool)) or value is None:
            sanitized[key] = value
        elif isinstance(value, list):
            sanitized[key] = [item for item in value if isinstance(item, (str, int, float, bool))]
        elif isinstance(value, dict):
            sanitized[key] = {
                nested_key: nested_value
                for nested_key, nested_value in value.items()
                if isinstance(nested_value, (str, int, float, bool))
            }
    return sanitized or None


def _memory_to_dict(memory: HuntMemory) -> dict[str, Any]:
    return {
        "id": str(memory.id),
        "organization_id": str(memory.organization_id),
        "memory_type": memory.memory_type,
        "summary": memory.summary,
        "metadata": memory.metadata_ or {},
        "created_at": memory.created_at.isoformat(),
    }


class HuntMemoryEngine:
    """Persistent memory access layer with org isolation and sanitization."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def store_hunt_memory(
        self,
        organization_id: UUID,
        memory_type: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> HuntMemory:
        memory = HuntMemory(
            organization_id=organization_id,
            memory_type=_normalize_memory_type(memory_type),
            summary=_sanitize_text(summary),
            metadata_=_sanitize_metadata(metadata),
        )
        self.db.add(memory)
        await self.db.flush()
        return memory

    async def retrieve_related_memory(
        self,
        organization_id: UUID,
        query: str,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        tokens = [token for token in _sanitize_text(query).lower().split() if len(token) > 2]
        stmt = select(HuntMemory).where(HuntMemory.organization_id == organization_id)

        if memory_type:
            stmt = stmt.where(HuntMemory.memory_type == _normalize_memory_type(memory_type))

        if tokens:
            like_clauses = [cast(HuntMemory.summary, String).ilike(f"%{token}%") for token in tokens[:8]]
            stmt = stmt.where(or_(*like_clauses) if len(like_clauses) > 1 else like_clauses[0])

        stmt = stmt.order_by(desc(HuntMemory.created_at)).limit(limit)
        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        if tokens and memories:
            scored: list[tuple[int, HuntMemory]] = []
            for memory in memories:
                haystack = f"{memory.summary} {json.dumps(memory.metadata_ or {}, default=str)}".lower()
                score = sum(1 for token in tokens if token in haystack)
                scored.append((score, memory))
            memories = [memory for score, memory in sorted(scored, key=lambda item: (-item[0], item[1].created_at), reverse=False) if score > 0]

        return [_memory_to_dict(memory) for memory in memories[:limit]]

    async def summarize_historical_patterns(
        self,
        organization_id: UUID,
        limit: int = 25,
    ) -> dict[str, Any]:
        stmt = (
            select(HuntMemory)
            .where(HuntMemory.organization_id == organization_id)
            .order_by(desc(HuntMemory.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        pattern_counts = Counter(memory.memory_type for memory in memories)
        recurring_topics = []
        for memory_type, count in pattern_counts.most_common():
            if count < 2:
                continue
            recurring_topics.append(
                {
                    "memory_type": memory_type,
                    "count": count,
                    "latest_summary": next((memory.summary for memory in memories if memory.memory_type == memory_type), ""),
                }
            )

        return {
            "organization_id": str(organization_id),
            "total_memories": len(memories),
            "memory_type_counts": dict(pattern_counts),
            "recurring_topics": recurring_topics,
            "recent_memories": [_memory_to_dict(memory) for memory in memories[: min(len(memories), 10)]],
        }

