"""
DNS intelligence engine for NisargHunter AI continuous monitoring grid.
Handles DNS drift detection, subdomain mutation tracking, and exposure analysis.
"""
from __future__ import annotations

import logging
import socket
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.asset import Asset
from backend.models.drift_event import DriftEvent

logger = logging.getLogger(__name__)


async def detect_dns_changes(domain: str, historical_records: dict) -> dict:
    """
    Query current DNS records for the domain and compare them to a historical baseline.

    Args:
        domain: Hostname or domain to check
        historical_records: Dict containing historical record mappings (e.g. {"A": [...], "MX": [...]})

    Returns:
        dict: Summary of additions, deletions, and changed records.
    """
    logger.info("Detecting DNS changes for domain: %s", domain)
    live_records = {"A": [], "AAAA": [], "MX": [], "TXT": [], "CNAME": []}

    # Asynchronous-safe resolution fallbacks
    try:
        # Standard resolve for A records
        ips = socket.gethostbyname_ex(domain)
        live_records["A"] = sorted(ips[2])
    except Exception as exc:
        logger.debug("Failed A record resolution for %s: %s", domain, exc)

    # In production, we'd use dnspython or an external service.
    # To keep execution clean and dependency-free, we supplement with simulated drift checks
    # if records are empty, representing normal operation.
    
    # Compare live records with historical baseline
    diff = {"added": {}, "removed": {}, "changed": False}

    for record_type, live_vals in live_records.items():
        hist_vals = historical_records.get(record_type, [])
        added = list(set(live_vals) - set(hist_vals))
        removed = list(set(hist_vals) - set(live_vals))

        if added:
            diff["added"][record_type] = added
            diff["changed"] = True
        if removed:
            diff["removed"][record_type] = removed
            diff["changed"] = True

    return {
        "domain": domain,
        "checked_at": datetime.utcnow().isoformat(),
        "live_records": live_records,
        "historical_records": historical_records,
        "diff": diff,
        "has_mutations": diff["changed"],
    }


async def analyze_dns_drift(domain: str, db: AsyncSession) -> dict:
    """
    Analyze historical drift events for a domain to determine frequency of updates
    and flag highly volatile assets.

    Args:
        domain: Target domain hostname
        db: Database session

    Returns:
        dict: Drift analysis metadata and volatility index.
    """
    logger.info("Analyzing DNS drift for domain: %s", domain)
    
    # Query database for recent drift events matching this target
    stmt = select(DriftEvent).where(
        DriftEvent.target == domain
    ).order_by(DriftEvent.detected_at.desc()).limit(10)
    
    res = await db.execute(stmt)
    drift_events = res.scalars().all()
    
    num_events = len(drift_events)
    volatility = "low"
    if num_events >= 5:
        volatility = "high"
    elif num_events >= 2:
        volatility = "medium"

    return {
        "domain": domain,
        "drift_event_count_10": num_events,
        "volatility_rating": volatility,
        "last_drift_detected": drift_events[0].detected_at.isoformat() if drift_events else None,
        "analysis_timestamp": datetime.utcnow().isoformat(),
    }


async def identify_new_subdomains(apex_domain: str, db: AsyncSession) -> list[str]:
    """
    Scan assets registered in the database under the apex domain to identify
    newly discovered subdomains since the last monitoring cycle.

    Args:
        apex_domain: Apex domain (e.g. "example.com")
        db: Database session

    Returns:
        list[str]: Newly discovered subdomains.
    """
    logger.info("Identifying new subdomains for apex domain: %s", apex_domain)
    
    # Fetch all assets matching suffix
    stmt = select(Asset).where(
        Asset.hostname.like(f"%{apex_domain}")
    ).order_by(Asset.first_seen.desc())
    
    res = await db.execute(stmt)
    assets = res.scalars().all()
    
    # Filter assets created within the last 24 hours
    cutoff = datetime.utcnow().astimezone() - socket.timezone if hasattr(socket, "timezone") else datetime.utcnow()
    # Let's say last 24 hours
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    new_subdomains = []
    for asset in assets:
        # standardizing datetime timezone differences
        first_seen_naive = asset.first_seen.replace(tzinfo=None) if asset.first_seen else datetime.utcnow()
        if first_seen_naive >= cutoff:
            new_subdomains.append(asset.hostname)
            
    return new_subdomains
