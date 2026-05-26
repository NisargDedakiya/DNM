from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Any

class ReportGenerateRequest(BaseModel):
    finding_id: UUID
    evidence_notes: Optional[str] = ""
    platform: Optional[str] = "hackerone"

class ReportUpdateRequest(BaseModel):
    title: Optional[str] = None
    severity: Optional[str] = None
    vulnerability_type: Optional[str] = None
    description: Optional[str] = None
    steps_to_reproduce: Optional[list[str]] = None
    impact: Optional[str] = None
    remediation: Optional[str] = None
    cvss_score: Optional[float] = None
    quality_score: Optional[int] = None
    quality_breakdown: Optional[dict[str, Any]] = None

class ReportResponse(BaseModel):
    id: UUID
    finding_id: UUID
    platform: str
    title: str
    severity: str
    vulnerability_type: str
    description: str
    steps_to_reproduce: list[str]
    impact: str
    remediation: str
    cvss_score: Optional[float] = None
    quality_score: int
    quality_breakdown: dict[str, Any]
    submitted_at: Optional[datetime] = None
    platform_submission_id: Optional[str] = None
    outcome: Optional[str] = None
    created_by_id: Optional[UUID] = None
    generated_by_ai: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
