"""
Pydantic schemas for scan validation and serialization.
"""
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ScanTypeEnum(str, Enum):
    """Scan types."""

    recon = "recon"
    surface = "surface"
    deep = "deep"
    manual = "manual"


class ScanStatusEnum(str, Enum):
    """Scan execution statuses."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ScanCreate(BaseModel):
    """Schema for creating new scan."""

    program_id: UUID = Field(..., description="Program to scan")
    scan_type: ScanTypeEnum = Field(
        default=ScanTypeEnum.recon,
        description="Type of scan to execute",
    )


class ScanResponse(BaseModel):
    """Schema for scan details response."""

    id: UUID
    program_id: UUID
    created_by_id: UUID | None
    scan_type: ScanTypeEnum
    status: ScanStatusEnum
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanStatusResponse(BaseModel):
    """Schema for scan status update."""

    scan_id: UUID
    status: ScanStatusEnum
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message: str | None = None


class ScanListResponse(BaseModel):
    """Schema for list of scans."""

    total: int
    scans: list[ScanResponse]


class SubdomainResult(BaseModel):
    """Schema for discovered subdomain."""

    subdomain: str
    source: str | None = None


class LiveHostResult(BaseModel):
    """Schema for live host detection."""

    url: str
    status_code: int | None
    title: str | None
    content_length: int | None
    port: int | None
    scheme: str | None


class ScanPipelineResult(BaseModel):
    """Schema for complete recon pipeline result."""

    target: str
    status: str = Field(description="Pipeline status: completed, failed, running")
    summary: dict | None = Field(
        default=None,
        description="Summary stats: total_subdomains, live_hosts",
    )
    stages: dict = Field(
        default_factory=dict,
        description="Results from each pipeline stage",
    )


class ScanExecutionRequest(BaseModel):
    """Schema for scan execution request."""

    program_id: UUID
    scan_type: ScanTypeEnum = Field(
        default=ScanTypeEnum.recon,
        description="Type of scan",
    )
    target: str | None = Field(
        default=None,
        description="Optional target override",
    )


class ScanResultsStorageSchema(BaseModel):
    """Schema for storing scan results."""

    scan_id: UUID
    stage: str = Field(description="Scanner stage: subfinder, httpx, etc")
    results: list[dict] = Field(description="Parsed results from scanner")
    raw_output: str | None = Field(default=None, description="Raw scanner output")
    status: str = Field(description="Stage status: success, failed, timeout")
