"""
Program schemas for API validation and response formatting.
Used for bug bounty program CRUD operations.
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProgramCreate(BaseModel):
    """Schema for creating a new program."""

    name: str = Field(..., min_length=1, max_length=255, description="Program name")
    platform: str = Field(..., min_length=1, max_length=100, description="Bug bounty platform")
    scope: str = Field(..., min_length=1, description="Program scope and targets")
    description: Optional[str] = Field(None, description="Optional program description")


class ProgramUpdate(BaseModel):
    """Schema for updating an existing program."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    platform: Optional[str] = Field(None, min_length=1, max_length=100)
    scope: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None)


class ProgramResponse(BaseModel):
    """Schema for individual program response."""

    id: UUID
    name: str
    platform: str
    scope: str
    description: Optional[str]
    created_by: UUID
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ProgramListResponse(BaseModel):
    """Schema for list of programs response."""

    total: int
    programs: list[ProgramResponse]
