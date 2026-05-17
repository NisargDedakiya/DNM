"""
Pydantic schemas for findings validation and serialization.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from backend.core.enums import FindingSeverity, FindingStatus


class FindingCreate(BaseModel):
    """Schema for creating a new finding."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Finding title/vulnerability name",
    )
    severity: FindingSeverity = Field(
        ...,
        description="Severity level: info, low, medium, high, critical",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Detailed finding description",
    )
    endpoint: str | None = Field(
        default=None,
        max_length=2048,
        description="Affected endpoint/URL",
    )
    evidence: str | None = Field(
        default=None,
        max_length=50000,
        description="Evidence/proof of vulnerability",
    )
    scan_id: UUID | None = Field(
        default=None,
        description="Optional scan that discovered this finding",
    )
    program_id: UUID = Field(
        ...,
        description="Program this finding belongs to",
    )


class FindingUpdate(BaseModel):
    """Schema for updating a finding."""

    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
        description="Finding title",
    )
    severity: FindingSeverity | None = Field(
        default=None,
        description="Severity level",
    )
    description: str | None = Field(
        default=None,
        min_length=10,
        max_length=10000,
        description="Detailed description",
    )
    endpoint: str | None = Field(
        default=None,
        max_length=2048,
        description="Affected endpoint",
    )
    evidence: str | None = Field(
        default=None,
        max_length=50000,
        description="Evidence/proof",
    )
    status: FindingStatus | None = Field(
        default=None,
        description="Finding status",
    )


class FindingResponse(BaseModel):
    """Schema for finding details response."""

    id: UUID
    program_id: UUID
    scan_id: UUID | None
    created_by_id: UUID | None
    title: str
    severity: FindingSeverity
    description: str
    endpoint: str | None
    evidence: str | None
    status: FindingStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FindingListResponse(BaseModel):
    """Schema for list of findings."""

    total: int = Field(description="Total findings count")
    findings: list[FindingResponse] = Field(description="List of findings")


class FindingFilterParams(BaseModel):
    """Schema for finding filter parameters."""

    severity: FindingSeverity | None = Field(
        default=None,
        description="Filter by severity",
    )
    status: FindingStatus | None = Field(
        default=None,
        description="Filter by status",
    )
    scan_id: UUID | None = Field(
        default=None,
        description="Filter by scan",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum results",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Result offset",
    )


class DeduplicateRequest(BaseModel):
    """Schema for finding deduplication check."""

    title: str = Field(description="Finding title")
    severity: FindingSeverity = Field(description="Finding severity")
    endpoint: str | None = Field(default=None, description="Affected endpoint")
    program_id: UUID = Field(description="Program to check duplicates in")
