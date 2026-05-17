"""
Structured realtime event schemas for websocket messages.

Defines pydantic models for common scan and finding events.
Uses Pydantic v2 Literal instead of deprecated const=True.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EventBase(BaseModel):
    event: str = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)


class ScanStarted(EventBase):
    event: Literal["scan_started"] = "scan_started"
    payload: dict = Field(default_factory=dict)


class ScanProgress(EventBase):
    event: Literal["scan_progress"] = "scan_progress"
    payload: dict = Field(default_factory=dict)


class ScanCompleted(EventBase):
    event: Literal["scan_completed"] = "scan_completed"
    payload: dict = Field(default_factory=dict)


class ScanFailed(EventBase):
    event: Literal["scan_failed"] = "scan_failed"
    payload: dict = Field(default_factory=dict)


class FindingCreated(EventBase):
    event: Literal["finding_created"] = "finding_created"
    payload: dict = Field(default_factory=dict)


def serialize_event(ev: EventBase) -> dict:
    """Return JSON-serializable dict for an event."""
    return ev.model_dump()
