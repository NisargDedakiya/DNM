"""
Continuous scheduler for continuous monitoring.
Orchestrates monitoring cycles, adapts polling frequencies, and prioritizes targets.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.organization import Organization
from backend.models.exposure_mutation import ExposureMutation
from backend.grid.monitoring_agent import monitor_asset, start_monitoring_agent

logger = logging.getLogger(__name__)


async def schedule_monitoring_cycle(db: AsyncSession) -> dict:
    """
    Fetch active organizations, prioritize their assets, and trigger monitoring checks.

    Args:
        db: Database session

    Returns:
        dict: Summary of the scheduled monitoring cycle execution.
    """
    logger.info("Starting scheduled continuous monitoring cycle")
    
    # Fetch organizations
    org_stmt = select(Organization).limit(100)
    org_res = await db.execute(org_stmt)
    organizations = org_res.scalars().all()
    
    processed_assets = 0
    triggered_mutations = 0
    cycle_details = []

    for org in organizations:
        # Resolve organization UUID
        org_id = UUID(org.id) if isinstance(org.id, str) else org.id
        
        # Start/Register Grid Agent for the org
        await start_monitoring_agent(org_id, db)
        
        # Prioritize targets
        targets = await prioritize_monitoring_targets(org_id, db)
        
        org_processed = 0
        org_mutations = 0
        for asset_id in targets:
            # Check adaptive frequency
            # To simulate, we assume all prioritized targets require a cycle check
            res = await monitor_asset(org_id, asset_id, db)
            org_processed += 1
            org_mutations += res.get("mutations_found", 0)
            
        processed_assets += org_processed
        triggered_mutations += org_mutations
        cycle_details.append({
            "org_id": str(org_id),
            "assets_checked": org_processed,
            "mutations_found": org_mutations,
        })

    return {
        "cycle_completed_at": datetime.utcnow().isoformat(),
        "total_organizations": len(organizations),
        "total_assets_monitored": processed_assets,
        "total_mutations_triggered": triggered_mutations,
        "details": cycle_details,
    }


async def prioritize_monitoring_targets(organization_id: UUID, db: AsyncSession) -> list[UUID]:
    """
    Prioritize assets for scanning based on risk score, severity, and scheduling rules.

    Args:
        organization_id: Organization context
        db: Database session

    Returns:
        list[UUID]: Prioritized asset UUIDs.
    """
    logger.info("[%s] Prioritizing continuous monitoring targets", organization_id)
    
    # Query assets sorted by risk score desc
    stmt = (
        select(Asset.id)
        .where(Asset.organization_id == organization_id)
        .order_by(desc(Asset.risk_score), desc(Asset.last_seen))
        .limit(15)
    )
    
    res = await db.execute(stmt)
    return [row for row in res.scalars().all()]


async def adapt_monitoring_frequency(asset_id: UUID, base_frequency: int, db: AsyncSession) -> int:
    """
    Adapt the checking frequency (in seconds) dynamically.
    Speeds up checks if mutations are frequent; slows down if the asset is stable.

    Args:
        asset_id: Target asset UUID
        base_frequency: Standard delay in seconds (e.g. 3600 seconds)
        db: Database session

    Returns:
        int: Adjusted check frequency in seconds.
    """
    logger.debug("Adapting monitoring frequency for asset: %s", asset_id)
    
    # Check mutations in the last 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    
    # Query mutations for this asset
    stmt = select(ExposureMutation).where(
        and_(
            ExposureMutation.created_at >= cutoff
        )
    )
    res = await db.execute(stmt)
    mutations = res.scalars().all()
    
    # Filter mutations matching this asset_id in JSON payload
    asset_mutations = [
        m for m in mutations 
        if m.asset.get("id") == str(asset_id)
    ]
    
    mutation_count = len(asset_mutations)
    
    # If volatile (frequent mutations), decrease check delay (poll more often)
    if mutation_count >= 5:
        adjusted_freq = int(base_frequency * 0.25)  # 4x faster
    elif mutation_count >= 2:
        adjusted_freq = int(base_frequency * 0.5)   # 2x faster
    elif mutation_count == 0:
        adjusted_freq = int(base_frequency * 2.0)   # 2x slower (cool down stable assets)
    else:
        adjusted_freq = base_frequency

    # Enforce safe bounds (e.g., minimum 60 seconds, maximum 24 hours)
    return max(60, min(adjusted_freq, 86400))
