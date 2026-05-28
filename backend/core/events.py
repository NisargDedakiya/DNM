from backend.events.event_schema import (
    EventType,
    SeverityLevel,
    BaseEvent,
    EventMetadata
)
from typing import Any, Dict, Optional
from pydantic import BaseModel

class ScanEventPayload(BaseModel):
    scan_id: str
    target: str
    status: str
    progress: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class FindingEventPayload(BaseModel):
    finding_id: str
    scan_id: str
    target: str
    title: str
    severity: Optional[SeverityLevel] = None
    ai_confidence: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

class ApprovalEventPayload(BaseModel):
    approval_id: str
    entity_type: str
    entity_id: str
    status: str
    reason: Optional[str] = None

class ReportEventPayload(BaseModel):
    report_id: str
    target: str
    summary: str
    status: str
