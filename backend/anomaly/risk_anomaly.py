"""
Risk anomaly engine for NisargHunter AI continuous monitoring grid.
Detects sudden risk spikes, correlates exposure anomalies, and identifies escalation patterns.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.anomaly_event import AnomalyEvent

logger = logging.getLogger(__name__)


async def detect_risk_spike(
    organization_id: UUID,
    asset_id: UUID,
    previous_score: float,
    new_score: float,
    db: AsyncSession,
) -> dict:
    """
    Evaluate if an asset's risk score has spiked abnormally.
    Triggers an AnomalyEvent if the spike is severe (e.g. increase > 30% or > 3.0 points).

    Args:
        organization_id: Organization context
        asset_id: UUID of target asset
        previous_score: Previous risk score
        new_score: New risk score
        db: Database session

    Returns:
        dict: Spike evaluation details, indicating if an event was created.
    """
    logger.info("[%s] Evaluating risk spike for asset %s (%s -> %s)", organization_id, asset_id, previous_score, new_score)
    
    score_diff = new_score - previous_score
    is_spike = False
    severity = "medium"
    reasons = []

    # Spike triggers
    if score_diff >= 3.0:
        is_spike = True
        severity = "high"
        reasons.append(f"Risk score increased suddenly by {score_diff:.2f} points.")
    elif previous_score > 0 and (score_diff / previous_score) >= 0.5:
        is_spike = True
        severity = "medium"
        reasons.append(f"Risk score inflated by {(score_diff / previous_score) * 100:.1f}%.")

    anomaly_record = None
    if is_spike:
        # Fetch asset hostname
        stmt = select(Asset).where(Asset.id == asset_id)
        res = await db.execute(stmt)
        asset = res.scalars().first()
        hostname = asset.hostname if asset else "unknown"

        summary_text = f"Risk spike on asset {hostname}: " + " | ".join(reasons)
        
        # Save AnomalyEvent
        anomaly_record = AnomalyEvent(
            organization_id=organization_id,
            anomaly_type="risk_spike",
            severity=severity,
            summary=summary_text,
            detected_at=datetime.utcnow(),
        )
        db.add(anomaly_record)
        await db.commit()
        await db.refresh(anomaly_record)
        logger.info("[%s] Risk spike anomaly logged: %s", organization_id, anomaly_record.id)

    return {
        "asset_id": str(asset_id),
        "is_spike": is_spike,
        "score_diff": score_diff,
        "anomaly_id": str(anomaly_record.id) if anomaly_record else None,
        "severity": severity,
    }


async def correlate_exposure_anomalies(organization_id: UUID, anomalies: list[dict], db: AsyncSession) -> dict:
    """
    Correlate multiple minor anomalies (e.g. DNS changes + auth mutations)
    occurring within a narrow timeline window to reveal complex attack behaviors.

    Args:
        organization_id: Organization context
        anomalies: List of anomaly event dicts
        db: Database session

    Returns:
        dict: Correlation analysis reporting complex threat vectors.
    """
    logger.info("[%s] Correlating %d anomalies", organization_id, len(anomalies))
    
    correlated_events = []
    
    # Simple correlation: find anomalies referencing the same hostnames/keywords
    # in their summary text within the session list.
    summary_matches: dict[str, list[dict]] = {}
    for a in anomalies:
        # Extract potential hostname indicators
        words = a.get("summary", "").split()
        for w in words:
            if "." in w or "asset" in w:
                summary_matches.setdefault(w, []).append(a)

    for keyword, matched_list in summary_matches.items():
        if len(matched_list) >= 2:
            correlated_events.append({
                "keyword": keyword,
                "anomaly_count": len(matched_list),
                "anomalies": [m.get("id") for m in matched_list],
                "description": f"Coordinated mutations detected containing pattern: '{keyword}'",
            })

    return {
        "organization_id": str(organization_id),
        "correlated_threat_count": len(correlated_events),
        "correlations": correlated_events,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def identify_escalation_patterns(organization_id: UUID, db: AsyncSession) -> list[dict]:
    """
    Search anomaly_events to locate coordinate escalations (e.g. sudden clusters of anomalies
    happening within the last 48 hours).

    Args:
        organization_id: Organization context
        db: Database session

    Returns:
        list[dict]: List of identified escalation patterns.
    """
    logger.info("[%s] Identifying escalation patterns", organization_id)
    
    cutoff = datetime.utcnow() - timedelta(hours=48)
    stmt = select(AnomalyEvent).where(
        and_(
            AnomalyEvent.organization_id == organization_id,
            AnomalyEvent.detected_at >= cutoff,
        )
    ).order_by(AnomalyEvent.detected_at.desc())
    
    res = await db.execute(stmt)
    events = res.scalars().all()

    patterns = []
    # If we have a sudden burst of anomalies (e.g., > 3 anomalies in last 48 hours)
    if len(events) >= 3:
        patterns.append({
            "pattern_type": "coordinated_attack_surge",
            "event_count": len(events),
            "severity": "high",
            "description": f"Surge of {len(events)} anomalies detected in the last 48 hours. Potential coordinated campaign.",
            "anomalies": [str(e.id) for e in events],
        })

    return patterns
