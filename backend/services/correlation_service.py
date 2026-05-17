"""
Findings correlation service: duplicate detection, clustering and linking.

Design notes:
- Non-destructive: findings are never deleted. Duplicates are flagged and linked via Redis sets.
- Deterministic fingerprints are used for exact duplicate detection.
- Similarity scoring is used to propose clusters without auto-merging.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.fingerprint import generate_finding_fingerprint
from backend.core.similarity import calculate_similarity
from backend.core.redis import get_redis
from backend.models.finding import Finding
from backend.models.finding import FindingStatus


async def detect_duplicates(db: AsyncSession, finding: Finding, threshold: float = 0.95) -> List[Tuple[Finding, float]]:
    """Detect duplicates for a given finding.

    Returns list of (candidate_finding, score) where score >= threshold.
    Exact fingerprint matches will be returned with score 1.0.
    Does NOT modify DB; it may mark status separately if caller requests.
    """
    fingerprint = generate_finding_fingerprint(finding.title, finding.endpoint, finding.severity.value if finding.severity else None)

    # Search same program for potential duplicates
    stmt = select(Finding).where(Finding.program_id == finding.program_id)
    res = await db.execute(stmt)
    candidates = res.scalars().all()
    matches: List[Tuple[Finding, float]] = []
    for c in candidates:
        if c.id == finding.id:
            continue
        fp_c = generate_finding_fingerprint(c.title, c.endpoint, c.severity.value if c.severity else None)
        if fp_c == fingerprint:
            matches.append((c, 1.0))
            continue
        score = calculate_similarity(finding.title, finding.endpoint, c.title, c.endpoint, getattr(finding.severity, 'value', None), getattr(c.severity, 'value', None))
        if score >= threshold:
            matches.append((c, score))

    return matches


async def cluster_findings(db: AsyncSession, program_id: UUID, similarity_threshold: float = 0.7) -> List[List[UUID]]:
    """Cluster findings within a program using greedy clustering.

    Returns list of clusters, each cluster is list of finding IDs.
    """
    stmt = select(Finding).where(Finding.program_id == program_id)
    res = await db.execute(stmt)
    findings = res.scalars().all()
    unvisited = set([f.id for f in findings])
    clusters: List[List[UUID]] = []
    by_id = {f.id: f for f in findings}

    while unvisited:
        current = unvisited.pop()
        seed = by_id[current]
        cluster = [current]
        to_check = list(unvisited)
        for fid in to_check:
            candidate = by_id[fid]
            score = calculate_similarity(seed.title, seed.endpoint, candidate.title, candidate.endpoint, getattr(seed.severity, 'value', None), getattr(candidate.severity, 'value', None))
            if score >= similarity_threshold:
                cluster.append(fid)
                unvisited.remove(fid)
        clusters.append(cluster)

    return clusters


async def correlate_finding(db: AsyncSession, finding: Finding, auto_mark_duplicate: bool = False, redis_prefix: str = "correlation") -> Dict[str, Any]:
    """Run correlation for a single finding.

    - Detect duplicates
    - Suggest related findings by similarity
    - Optionally mark exact duplicates as status duplicate (non-destructive)
    - Store relationships in Redis sets:
        - correlation:duplicates:{finding_id} -> canonical_id
        - correlation:related:{finding_id} -> set(related_ids)
    Returns a summary dict.
    """
    matches = await detect_duplicates(db, finding)
    redis = await get_redis()
    dup_key = f"{redis_prefix}:duplicates:{str(finding.id)}"
    related_key = f"{redis_prefix}:related:{str(finding.id)}"
    summary: Dict[str, Any] = {"duplicates": [], "related": []}

    # Exact fingerprint duplicates have score 1.0
    canonical_id: Optional[str] = None
    for cand, score in matches:
        summary["duplicates"].append({"id": str(cand.id), "score": score})
        if score == 1.0 and canonical_id is None:
            canonical_id = str(cand.id)

    if canonical_id:
        # mark key to canonical
        await redis.set(dup_key, canonical_id)
        if auto_mark_duplicate:
            # mark the finding as duplicate in DB (non-destructive)
            finding.status = FindingStatus.duplicate
            db.add(finding)
            await db.flush()

    # related suggestions using a lower threshold
    # scan candidates again with lower threshold
    stmt = select(Finding).where(Finding.program_id == finding.program_id)
    res = await db.execute(stmt)
    candidates = res.scalars().all()
    for c in candidates:
        if c.id == finding.id:
            continue
        score = calculate_similarity(finding.title, finding.endpoint, c.title, c.endpoint, getattr(finding.severity, 'value', None), getattr(c.severity, 'value', None))
        if 0.4 <= score < 1.0:
            summary["related"].append({"id": str(c.id), "score": score})
            await redis.sadd(related_key, str(c.id))

    return summary


async def link_related_findings(finding_id: UUID, related_id: UUID, redis_prefix: str = "correlation") -> None:
    """Add a bidirectional related link in Redis sets. Non-destructive.
    """
    redis = await get_redis()
    await redis.sadd(f"{redis_prefix}:related:{str(finding_id)}", str(related_id))
    await redis.sadd(f"{redis_prefix}:related:{str(related_id)}", str(finding_id))
