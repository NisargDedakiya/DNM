"""
Assets API routes: list assets and related endpoints/technologies.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.services.program_service import ProgramService
from backend.schemas.asset import AssetResponse, AssetDetailResponse, EndpointResponse, TechnologyResponse
from backend.schemas.asset import AssetIngestRequest, EndpointIngestRequest, TechnologyIngestRequest
from backend.models.asset import Asset
from backend.models.endpoint import Endpoint
from backend.models.technology import Technology

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=List[AssetResponse])
async def list_assets(program_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ps = ProgramService(db)
    prog = await ps.get_program_by_id(program_id, user.id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found or not owned")

    result = await db.execute(select(Asset).where(Asset.program_id == program_id))
    assets = result.scalars().all()
    return assets


@router.get("/{asset_id}", response_model=AssetDetailResponse)
async def get_asset(asset_id: str, program_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ps = ProgramService(db)
    prog = await ps.get_program_by_id(program_id, user.id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found or not owned")

    result = await db.execute(select(Asset).where(Asset.id == asset_id, Asset.program_id == program_id))
    asset = result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # load endpoints and technologies via relationships
    await db.refresh(asset)
    return asset


@router.get("/{asset_id}/endpoints", response_model=List[EndpointResponse])
async def get_asset_endpoints(asset_id: str, program_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ps = ProgramService(db)
    prog = await ps.get_program_by_id(program_id, user.id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found or not owned")

    result = await db.execute(select(Endpoint).where(Endpoint.asset_id == asset_id))
    eps = result.scalars().all()
    return eps


@router.get("/{asset_id}/technologies", response_model=List[TechnologyResponse])
async def get_asset_technologies(asset_id: str, program_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ps = ProgramService(db)
    prog = await ps.get_program_by_id(program_id, user.id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found or not owned")

    result = await db.execute(select(Technology).where(Technology.asset_id == asset_id))
    techs = result.scalars().all()
    return techs



@router.post("/ingest/asset", response_model=AssetResponse)
async def ingest_asset(program_id: str, payload: AssetIngestRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ps = ProgramService(db)
    prog = await ps.get_program_by_id(program_id, user.id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found or not owned")

    from backend.services.asset_service import upsert_asset

    asset = await upsert_asset(db, program_id, payload.hostname, payload.ip_address, payload.is_alive)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.post("/ingest/endpoint", response_model=EndpointResponse)
async def ingest_endpoint(program_id: str, payload: EndpointIngestRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ps = ProgramService(db)
    prog = await ps.get_program_by_id(program_id, user.id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found or not owned")

    # ensure asset belongs to program
    from backend.services.asset_service import add_endpoint
    # ensure asset belongs to program
    from backend.models.asset import Asset as AssetModel
    ares = await db.execute(select(AssetModel).where(AssetModel.id == payload.asset_id))
    asset = ares.scalars().first()
    if not asset or str(asset.program_id) != str(program_id):
        raise HTTPException(status_code=404, detail="Asset not found in program")

    ep = await add_endpoint(db, payload.asset_id, payload.url, payload.method, payload.status_code, payload.content_type)
    await db.commit()
    await db.refresh(ep)
    return ep


@router.post("/ingest/technology", response_model=TechnologyResponse)
async def ingest_technology(program_id: str, payload: TechnologyIngestRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ps = ProgramService(db)
    prog = await ps.get_program_by_id(program_id, user.id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found or not owned")

    from backend.services.asset_service import add_technology
    # ensure asset belongs to program
    from backend.models.asset import Asset as AssetModel
    ares = await db.execute(select(AssetModel).where(AssetModel.id == payload.asset_id))
    asset = ares.scalars().first()
    if not asset or str(asset.program_id) != str(program_id):
        raise HTTPException(status_code=404, detail="Asset not found in program")

    tech = await add_technology(db, payload.asset_id, payload.name, payload.version, payload.confidence_score)
    await db.commit()
    await db.refresh(tech)
    return tech
