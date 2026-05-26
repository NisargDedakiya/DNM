"""
Public REST API for developer ecosystem consumers.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_db
from backend.models.attack_path import AttackPath
from backend.models.exposure_event import ExposureEvent
from backend.models.finding import Finding
from backend.models.monitoring_rule import MonitoringRule
from backend.models.threat_intel import ThreatIntel
from backend.services.developer_service import DeveloperService

router = APIRouter(prefix="/public", tags=["public-api"])


async def get_developer_service(db: AsyncSession = Depends(get_db)) -> DeveloperService:
    return DeveloperService(db)


async def _authorize(
    organization_id: UUID,
    api_key: str = Header(..., alias="X-API-Key"),
    service: DeveloperService = Depends(get_developer_service),
) -> dict:
    return await service.validate_developer_request(
        organization_id=organization_id,
        api_key_secret=api_key,
        endpoint="public",
    )


def _paginate(page: int, page_size: int) -> tuple[int, int]:
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    return page, page_size


@router.get("/findings")
async def public_findings(
    organization_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: str | None = None,
    api_context: dict = Depends(_authorize),
    db: AsyncSession = Depends(get_db),
) -> dict:
    page, page_size = _paginate(page, page_size)
    query = select(Finding).where(Finding.organization_id == organization_id)
    if severity:
        query = query.where(Finding.severity == severity)
    query = query.order_by(Finding.created_at.desc())
    total = await db.scalar(select(func.count(Finding.id)).where(Finding.organization_id == organization_id))
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()
    return {
        "data": [
            {
                "id": item.id,
                "organization_id": item.organization_id,
                "program_id": item.program_id,
                "title": item.title,
                "severity": item.severity.value if hasattr(item.severity, "value") else str(item.severity),
                "status": item.status.value if hasattr(item.status, "value") else str(item.status),
                "endpoint": item.endpoint,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "pagination": {"page": page, "page_size": page_size, "total": int(total or 0)},
    }


@router.get("/attack-paths")
async def public_attack_paths(
    organization_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    api_context: dict = Depends(_authorize),
    db: AsyncSession = Depends(get_db),
) -> dict:
    page, page_size = _paginate(page, page_size)
    query = select(AttackPath).where(AttackPath.organization_id == organization_id).order_by(AttackPath.created_at.desc())
    total = await db.scalar(select(func.count(AttackPath.id)).where(AttackPath.organization_id == organization_id))
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()
    return {
        "data": [
            {
                "id": item.id,
                "organization_id": item.organization_id,
                "source_asset": item.source_asset,
                "target_asset": item.target_asset,
                "severity": item.severity,
                "exploitability_score": item.exploitability_score,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "pagination": {"page": page, "page_size": page_size, "total": int(total or 0)},
    }


@router.get("/exposure-events")
async def public_exposure_events(
    organization_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    api_context: dict = Depends(_authorize),
    db: AsyncSession = Depends(get_db),
) -> dict:
    page, page_size = _paginate(page, page_size)
    query = select(ExposureEvent).where(ExposureEvent.organization_id == organization_id).order_by(ExposureEvent.created_at.desc())
    total = await db.scalar(select(func.count(ExposureEvent.id)).where(ExposureEvent.organization_id == organization_id))
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()
    return {
        "data": [
            {
                "id": item.id,
                "organization_id": item.organization_id,
                "asset": item.asset,
                "event_type": item.event_type,
                "severity": item.severity,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "pagination": {"page": page, "page_size": page_size, "total": int(total or 0)},
    }


@router.get("/threat-intelligence")
async def public_threat_intelligence(
    organization_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    api_context: dict = Depends(_authorize),
    db: AsyncSession = Depends(get_db),
) -> dict:
    page, page_size = _paginate(page, page_size)
    query = select(ThreatIntel).where(ThreatIntel.organization_id == organization_id).order_by(ThreatIntel.created_at.desc())
    total = await db.scalar(select(func.count(ThreatIntel.id)).where(ThreatIntel.organization_id == organization_id))
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()
    return {
        "data": [
            {
                "id": item.id,
                "organization_id": item.organization_id,
                "asset": item.asset,
                "intelligence_type": item.intelligence_type,
                "severity": item.severity,
                "summary": item.summary,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "pagination": {"page": page, "page_size": page_size, "total": int(total or 0)},
    }


@router.get("/monitoring-status")
async def public_monitoring_status(
    organization_id: UUID,
    api_context: dict = Depends(_authorize),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rules = await db.execute(
        select(MonitoringRule).where(MonitoringRule.organization_id == organization_id).order_by(MonitoringRule.created_at.desc()),
    )
    rule_rows = rules.scalars().all()
    total_rules = len(rule_rows)
    enabled_rules = sum(1 for rule in rule_rows if rule.enabled)
    active_rules = sum(1 for rule in rule_rows if getattr(rule, "is_active", True))
    return {
        "organization_id": organization_id,
        "summary": {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "active_rules": active_rules,
        },
        "rules": [
            {
                "id": rule.id,
                "name": rule.name,
                "program_id": rule.program_id,
                "frequency": rule.frequency.value if hasattr(rule.frequency, "value") else str(rule.frequency),
                "enabled": rule.enabled,
                "last_run_at": rule.last_run_at,
                "last_run_status": rule.last_run_status,
                "created_at": rule.created_at,
            }
            for rule in rule_rows
        ],
    }
