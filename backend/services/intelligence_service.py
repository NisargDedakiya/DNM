"""
Intelligence service: build graph, map relationships, exposure and historical analysis.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.technology import Technology
from backend.services.priority_service import calculate_priority_score


async def build_asset_graph(db: AsyncSession, program_id: UUID) -> Dict[str, Any]:
    """Return a simple knowledge graph mapping assets -> endpoints -> technologies."""
    stmt = select(Asset).where(Asset.program_id == program_id)
    res = await db.execute(stmt)
    assets = res.scalars().all()
    graph = {str(a.id): {"hostname": a.hostname, "ip": a.ip_address, "endpoints": [], "technologies": []} for a in assets}

    # fetch endpoints and technologies in program assets
    asset_ids = [a.id for a in assets]
    if not asset_ids:
        return graph

    stmt2 = select(Endpoint).where(Endpoint.asset_id.in_(asset_ids))
    res2 = await db.execute(stmt2)
    eps = res2.scalars().all()
    for e in eps:
        graph[str(e.asset_id)]["endpoints"].append({"id": str(e.id), "path": e.path, "method": e.method, "status_code": e.status_code})

    stmt3 = select(Technology).where(Technology.asset_id.in_(asset_ids))
    res3 = await db.execute(stmt3)
    techs = res3.scalars().all()
    for t in techs:
        graph[str(t.asset_id)]["technologies"].append({"id": str(t.id), "name": t.name, "version": t.version, "confidence": t.confidence_score})

    return graph


async def calculate_asset_risk(db: AsyncSession, asset_id: UUID) -> float:
    """Calculate a heuristic risk score for an asset.

    Uses endpoints count and technologies as signals; delegates to priority scoring where possible.
    """
    stmt = select(Asset).where(Asset.id == asset_id)
    res = await db.execute(stmt)
    asset = res.scalars().first()
    if not asset:
        return 0.0

    # Basic heuristic
    ep_count = len(asset.endpoints or [])
    tech_count = len(asset.technologies or [])
    base = min(1.0, 0.1 + 0.05 * ep_count + 0.05 * tech_count)

    # if technologies include known risky techs, bump
    risky = {"php", "wordpress", "tomcat", "jdk", "openssl"}
    has_risky = any(t.name.lower() in risky for t in (asset.technologies or []))
    if has_risky:
        base = min(1.0, base + 0.25)

    # store on asset (non-destructive update should be done by caller)
    return base


async def detect_asset_changes(db: AsyncSession, asset_id: UUID) -> Dict[str, Any]:
    """Detect recent changes on an asset (new endpoints/techs) and return a summary."""
    stmt = select(Asset).where(Asset.id == asset_id)
    res = await db.execute(stmt)
    asset = res.scalars().first()
    if not asset:
        return {}

    # naive detection: compare first_seen/last_seen ranges for endpoints/technologies
    new_eps = [e for e in (asset.endpoints or []) if e.first_seen == e.last_seen]
    new_tech = [t for t in (asset.technologies or []) if t.first_detected == asset.last_seen]
    return {"new_endpoints": [str(e.id) for e in new_eps], "new_technologies": [str(t.id) for t in new_tech]}


async def map_relationships(db: AsyncSession, program_id: UUID) -> Dict[str, List[str]]:
    """Map simple relationships: shared IP -> hostnames, subdomain groups.

    Returns mapping keys: 'ip_to_hosts', 'subdomain_groups'
    """
    stmt = select(Asset).where(Asset.program_id == program_id)
    res = await db.execute(stmt)
    assets = res.scalars().all()
    ip_map = defaultdict(list)
    sub_map = defaultdict(list)
    for a in assets:
        if a.ip_address:
            ip_map[a.ip_address].append(a.hostname)
        # split hostname for subdomain grouping
        parts = a.hostname.split(".")
        if len(parts) >= 3:
            base = ".".join(parts[-2:])
            sub_map[base].append(a.hostname)

    return {"ip_to_hosts": dict(ip_map), "subdomain_groups": dict(sub_map)}
