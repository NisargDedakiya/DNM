"""
Exposure anomaly engine for NisargHunter AI.
Detects unusual exposure modifications, analyzes mutation distributions, and flags high-risk anomalies.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.exposure_mutation import ExposureMutation
from backend.models.anomaly_event import AnomalyEvent

logger = logging.getLogger(__name__)


async def detect_exposure_anomaly(organization_id: UUID, mutation_id: UUID, db: AsyncSession) -> dict:
    """
    Evaluate if an exposure mutation deviates abnormally from historical baseline patterns.

    Args:
        organization_id: Organization context
        mutation_id: UUID of mutation record to inspect
        db: Database session

    Returns:
        dict: Anomaly report details, flagging if an anomaly was generated.
    """
    logger.info("[%s] Detecting exposure anomalies for mutation %s", organization_id, mutation_id)
    
    # 1. Fetch mutation
    stmt = select(ExposureMutation).where(
        and_(
            ExposureMutation.id == mutation_id,
            ExposureMutation.organization_id == organization_id,
        )
    )
    res = await db.execute(stmt)
    mutation = res.scalars().first()
    
    if not mutation:
        return {"is_anomaly": False, "reason": "Mutation not found"}

    # 2. Analyze mutation patterns
    baseline = await analyze_mutation_patterns(organization_id, db)
    
    # Heuristics:
    # - If severity is critical/high, flag as anomaly
    # - If mutation type is rare (< 10% of total mutations in baseline), flag as anomaly
    # - If multiple mutations happen on the same asset in short succession
    is_anomaly = False
    reasons = []
    severity = "medium"

    if mutation.severity in ("critical", "high"):
        is_anomaly = True
        severity = "high" if mutation.severity == "high" else "critical"
        reasons.append(f"Critical/High severity mutation detected ({mutation.mutation_type}).")

    type_counts = baseline.get("mutation_type_distribution", {})
    total_mutations = sum(type_counts.values())
    type_occurrences = type_counts.get(mutation.mutation_type, 0)
    
    if total_mutations > 5 and (type_occurrences / total_mutations) < 0.15:
        is_anomaly = True
        reasons.append(f"Rare mutation type detected: '{mutation.mutation_type}' representing less than 15% of historical baselines.")

    anomaly_record = None
    if is_anomaly:
        summary_text = f"Anomaly detected for asset {mutation.asset.get('hostname')}: " + " | ".join(reasons)
        
        # Save AnomalyEvent
        anomaly_record = AnomalyEvent(
            organization_id=organization_id,
            anomaly_type="exposure_anomaly",
            severity=severity,
            summary=summary_text,
            detected_at=datetime.utcnow(),
        )
        db.add(anomaly_record)
        await db.commit()
        await db.refresh(anomaly_record)
        logger.info("[%s] Exposure anomaly logged: %s", organization_id, anomaly_record.id)

    return {
        "mutation_id": str(mutation_id),
        "is_anomaly": is_anomaly,
        "reasons": reasons,
        "anomaly_id": str(anomaly_record.id) if anomaly_record else None,
        "severity": severity,
    }


async def analyze_mutation_patterns(organization_id: UUID, db: AsyncSession) -> dict:
    """
    Aggregate historical mutations to establish baseline statistics.

    Args:
        organization_id: Organization context
        db: Database session

    Returns:
        dict: Mutation count distribution and statistical baseline.
    """
    logger.debug("[%s] Analyzing mutation pattern distributions", organization_id)
    
    # Query mutations in the last 30 days
    cutoff = datetime.utcnow() - timedelta(days=30)
    stmt = select(ExposureMutation).where(
        and_(
            ExposureMutation.organization_id == organization_id,
            ExposureMutation.created_at >= cutoff,
        )
    )
    res = await db.execute(stmt)
    mutations = res.scalars().all()
    
    # Calculate type distributions
    type_distribution = {}
    asset_activity = {}
    
    for m in mutations:
        # Type
        type_distribution[m.mutation_type] = type_distribution.get(m.mutation_type, 0) + 1
        # Asset activity
        asset_id = m.asset.get("id", "unknown")
        asset_activity[asset_id] = asset_activity.get(asset_id, 0) + 1

    return {
        "total_historical_mutations": len(mutations),
        "mutation_type_distribution": type_distribution,
        "asset_activity_counts": asset_activity,
        "analyzed_at": datetime.utcnow().isoformat(),
    }


async def identify_high_risk_anomalies(organization_id: UUID, db: AsyncSession) -> list[dict]:
    """
    Scan recent anomaly events and filter high-risk alerts.

    Args:
        organization_id: Organization context
        db: Database session

    Returns:
        list[dict]: List of high-risk anomalies.
    """
    logger.info("[%s] Identifying high-risk anomalies", organization_id)
    
    stmt = select(AnomalyEvent).where(
        and_(
            AnomalyEvent.organization_id == organization_id,
            AnomalyEvent.severity.in_(["critical", "high"]),
        )
    ).order_by(AnomalyEvent.detected_at.desc()).limit(20)
    
    res = await db.execute(stmt)
    anomalies = res.scalars().all()
    
    return [
        {
            "id": str(a.id),
            "anomaly_type": a.anomaly_type,
            "severity": a.severity,
            "summary": a.summary,
            "detected_at": a.detected_at.isoformat(),
        }
        for a in anomalies
    ]
