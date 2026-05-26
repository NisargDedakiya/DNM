"""
Grid monitoring agent orchestration.
Manages agent heartbeats, performs asset inspections, and generates mutation events.
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.grid_agent import GridAgent
from backend.models.exposure_mutation import ExposureMutation
from backend.grid.dns_intelligence import detect_dns_changes
from backend.grid.cloud_exposure import analyze_cloud_exposure
from backend.grid.auth_mutation_detector import detect_auth_changes

logger = logging.getLogger(__name__)


async def start_monitoring_agent(organization_id: UUID, db: AsyncSession) -> GridAgent:
    """
    Register or activate a GridAgent for the given organization.
    Updates the agent status to "active" and updates heartbeat.

    Args:
        organization_id: Organization context
        db: Database session

    Returns:
        GridAgent: Registered agent record.
    """
    logger.info("[%s] Starting monitoring agent", organization_id)
    
    # Check for existing agent
    stmt = select(GridAgent).where(
        GridAgent.organization_id == organization_id
    ).limit(1)
    
    res = await db.execute(stmt)
    agent = res.scalars().first()
    
    now = datetime.utcnow()
    
    if agent:
        agent.status = "active"
        agent.last_heartbeat = now
    else:
        agent = GridAgent(
            organization_id=organization_id,
            status="active",
            monitored_assets={"asset_ids": []},
            last_heartbeat=now,
        )
        db.add(agent)
        
    await db.commit()
    await db.refresh(agent)
    return agent


async def monitor_asset(organization_id: UUID, asset_id: UUID, db: AsyncSession) -> dict:
    """
    Run DNS drift, cloud exposure, and authentication mutation checks on the asset.

    Args:
        organization_id: Organization context
        asset_id: UUID of target asset
        db: Database session

    Returns:
        dict: Monitoring outcomes and identified mutations.
    """
    logger.info("[%s] Monitoring asset %s", organization_id, asset_id)
    
    # 1. Fetch asset details
    stmt = select(Asset).where(
        Asset.id == asset_id,
        Asset.organization_id == organization_id
    )
    res = await db.execute(stmt)
    asset = res.scalars().first()
    
    if not asset:
        logger.warning("Asset %s not found under org %s", asset_id, organization_id)
        return {"status": "error", "message": "Asset not found"}

    mutations = []
    
    # 2. DNS Checks
    historical_dns = {"A": [asset.ip_address] if asset.ip_address else []}
    dns_res = await detect_dns_changes(asset.hostname, historical_dns)
    if dns_res.get("has_mutations"):
        mutations.append({
            "mutation_type": "dns_drift",
            "severity": "medium",
            "summary": f"DNS records changed for {asset.hostname}: {dns_res['diff']}",
        })

    # 3. Cloud Checks
    cloud_res = await analyze_cloud_exposure(asset.hostname)
    if cloud_res.get("risk_score", 0) > 0:
        mutations.append({
            "mutation_type": "cloud_exposure",
            "severity": cloud_res.get("risk_level", "medium"),
            "summary": f"Cloud exposure detected: {', '.join(cloud_res['exposures'])}",
        })

    # 4. Auth Checks
    dummy_auth_endpoints = [{"path": "/api/login", "method": "POST", "mfa_enabled": False}]
    auth_res = await detect_auth_changes(asset.id, dummy_auth_endpoints, db)
    if auth_res.get("has_mutations"):
        mutations.append({
            "mutation_type": "auth_mutation",
            "severity": "high",
            "summary": f"Authentication surface mutated: {len(auth_res['added_endpoints'])} added, {len(auth_res['modified_endpoints'])} modified endpoints.",
        })

    # 5. Emit mutations if any found
    mutation_records = []
    for mut in mutations:
        record = await emit_exposure_update(
            organization_id=organization_id,
            asset_id=asset.id,
            mutation_data=mut,
            db=db,
        )
        mutation_records.append({
            "id": str(record.id),
            "mutation_type": record.mutation_type,
            "severity": record.severity,
            "summary": record.summary,
        })
        
    # Update agent heartbeat
    agent_stmt = select(GridAgent).where(GridAgent.organization_id == organization_id).limit(1)
    agent_res = await db.execute(agent_stmt)
    agent = agent_res.scalars().first()
    if agent:
        agent.last_heartbeat = datetime.utcnow()
        # Add asset to list of monitored assets if not already there
        assets_list = agent.monitored_assets.get("asset_ids", [])
        if str(asset_id) not in assets_list:
            assets_list.append(str(asset_id))
            agent.monitored_assets = {"asset_ids": assets_list}
        await db.commit()

    return {
        "asset_id": str(asset_id),
        "checked_at": datetime.utcnow().isoformat(),
        "mutations_found": len(mutations),
        "details": mutation_records,
    }


async def emit_exposure_update(organization_id: UUID, asset_id: UUID, mutation_data: dict, db: AsyncSession) -> ExposureMutation:
    """
    Log an ExposureMutation to the database.

    Args:
        organization_id: Organization context
        asset_id: UUID of target asset
        mutation_data: Dict detailing the mutation type, severity, and description
        db: Database session

    Returns:
        ExposureMutation: Created database record.
    """
    logger.info("[%s] Emitting exposure update for asset %s", organization_id, asset_id)
    
    # Locate asset hostname for JSON payload
    stmt = select(Asset).where(Asset.id == asset_id)
    res = await db.execute(stmt)
    asset = res.scalars().first()
    
    asset_payload = {
        "id": str(asset_id),
        "hostname": asset.hostname if asset else "unknown",
        "ip_address": asset.ip_address if asset else None,
    }
    
    mutation = ExposureMutation(
        organization_id=organization_id,
        asset=asset_payload,
        mutation_type=mutation_data.get("mutation_type", "general"),
        severity=mutation_data.get("severity", "info"),
        summary=mutation_data.get("summary", "Asset mutation detected"),
    )
    
    db.add(mutation)
    await db.commit()
    await db.refresh(mutation)
    
    return mutation
