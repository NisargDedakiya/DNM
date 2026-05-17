"""
Asset service: upsert assets, endpoints and technologies.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.fingerprint import normalize_endpoint
from backend.core.scope_validator import normalize_domain
from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.technology import Technology


async def upsert_asset(db: AsyncSession, program_id, hostname: str, ip_address: Optional[str] = None, is_alive: bool = True) -> Asset:
    """Create or update an asset by (program_id, normalized hostname)."""
    nh = normalize_domain(hostname)
    stmt = select(Asset).where(Asset.program_id == program_id, Asset.hostname == nh)
    res = await db.execute(stmt)
    asset = res.scalars().first()
    now = datetime.utcnow()
    if not asset:
        asset = Asset(program_id=program_id, hostname=nh, ip_address=ip_address, is_alive=is_alive, first_seen=now, last_seen=now, risk_score=0.0)
        db.add(asset)
        await db.flush()
        await db.refresh(asset)
        # index into Redis graph
        from backend.services.graph_service import index_asset
        try:
            await index_asset(str(asset.id), str(program_id), nh, ip_address)
        except Exception:
            # graph updates should not break ingestion
            pass
        return asset

    # update existing
    asset.ip_address = ip_address or asset.ip_address
    asset.is_alive = is_alive
    asset.last_seen = now
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    # update graph index
    from backend.services.graph_service import index_asset
    try:
        await index_asset(str(asset.id), str(program_id), nh, ip_address)
    except Exception:
        pass
    return asset


async def update_asset_status(db: AsyncSession, asset_id, is_alive: bool) -> Asset | None:
    stmt = select(Asset).where(Asset.id == asset_id)
    res = await db.execute(stmt)
    asset = res.scalars().first()
    if not asset:
        return None
    asset.is_alive = is_alive
    asset.last_seen = datetime.utcnow()
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


async def add_endpoint(db: AsyncSession, asset_id, path: str, method: str = "GET", status_code: Optional[int] = None, content_type: Optional[str] = None) -> Endpoint:
    np = normalize_endpoint(path) or path
    stmt = select(Endpoint).where(Endpoint.asset_id == asset_id, Endpoint.path == np)
    res = await db.execute(stmt)
    ep = res.scalars().first()
    now = datetime.utcnow()
    if not ep:
        ep = Endpoint(asset_id=asset_id, path=np, method=method.upper(), status_code=status_code, content_type=content_type, first_seen=now, last_seen=now)
        db.add(ep)
        await db.flush()
        await db.refresh(ep)
        # index endpoint
        from backend.services.graph_service import index_endpoint
        try:
            await index_endpoint(str(asset_id), str(ep.id), np)
        except Exception:
            pass
        return ep

    ep.method = method.upper()
    ep.status_code = status_code or ep.status_code
    ep.content_type = content_type or ep.content_type
    ep.last_seen = now
    db.add(ep)
    await db.flush()
    await db.refresh(ep)
    # update graph if necessary
    from backend.services.graph_service import index_endpoint
    try:
        await index_endpoint(str(asset_id), str(ep.id), np)
    except Exception:
        pass
    return ep


async def add_technology(db: AsyncSession, asset_id, name: str, version: Optional[str], confidence_score: float = 0.5) -> Technology:
    stmt = select(Technology).where(Technology.asset_id == asset_id, Technology.name == name)
    res = await db.execute(stmt)
    tech = res.scalars().first()
    now = datetime.utcnow()
    if not tech:
        tech = Technology(asset_id=asset_id, name=name, version=version, confidence_score=confidence_score, first_detected=now)
        db.add(tech)
        await db.flush()
        await db.refresh(tech)
        from backend.services.graph_service import index_technology
        try:
            await index_technology(str(asset_id), str(tech.id), name, version, confidence_score)
        except Exception:
            pass
        return tech

    # update best known version and confidence
    tech.version = version or tech.version
    # keep max confidence
    tech.confidence_score = max(tech.confidence_score, confidence_score)
    db.add(tech)
    await db.flush()
    await db.refresh(tech)
    from backend.services.graph_service import index_technology
    try:
        await index_technology(str(asset_id), str(tech.id), name, version, confidence_score)
    except Exception:
        pass
    return tech
