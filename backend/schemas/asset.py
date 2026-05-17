"""
Pydantic schemas for asset inventory and intelligence responses.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EndpointResponse(BaseModel):
    id: UUID
    asset_id: UUID
    path: str
    method: str
    status_code: int | None
    content_type: str | None
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


class TechnologyResponse(BaseModel):
    id: UUID
    asset_id: UUID
    name: str
    version: str | None
    confidence_score: float
    first_detected: datetime

    class Config:
        from_attributes = True


class AssetResponse(BaseModel):
    id: UUID
    program_id: UUID
    hostname: str
    ip_address: str | None
    is_alive: bool
    first_seen: datetime
    last_seen: datetime
    risk_score: float

    class Config:
        from_attributes = True


class AssetDetailResponse(AssetResponse):
    endpoints: list[EndpointResponse] = Field(default_factory=list)
    technologies: list[TechnologyResponse] = Field(default_factory=list)


class AssetIngestRequest(BaseModel):
    hostname: str = Field(..., description="Discovered hostname")
    ip_address: str | None = Field(default=None, description="IP address if available")
    is_alive: bool = Field(default=True)


class EndpointIngestRequest(BaseModel):
    asset_id: UUID
    url: str = Field(..., description="URL or path discovered")
    method: str = Field(default="GET")
    status_code: int | None = None
    content_type: str | None = None


class TechnologyIngestRequest(BaseModel):
    asset_id: UUID
    name: str
    version: str | None = None
    confidence_score: float = Field(default=0.5)

