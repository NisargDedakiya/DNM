"""
Pydantic schemas for AI triage and report endpoints.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List
from uuid import UUID

from backend.core.enums import FindingSeverity


class TriageRequest(BaseModel):
    finding_id: UUID = Field(..., description="Finding to triage")


class TriageResponse(BaseModel):
    recommended_severity: FindingSeverity
    explanation: str
    remediation: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class ReportRequest(BaseModel):
    finding_ids: List[UUID] = Field(..., description="List of finding IDs to generate reports for")


class ReportItem(BaseModel):
    finding_id: UUID
    report_id: UUID | None
    content: str


class ReportResponse(BaseModel):
    reports: List[ReportItem]
