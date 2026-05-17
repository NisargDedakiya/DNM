"""
Organization schemas for API validation and response formatting.
Used for team collaboration and RBAC operations.
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class OrganizationCreate(BaseModel):
    """Schema for creating a new organization."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organization name",
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="URL-friendly organization identifier",
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional organization description",
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug contains only alphanumeric and hyphens."""
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("Slug must contain only alphanumeric characters, hyphens, and underscores")
        return v.lower()


class OrganizationUpdate(BaseModel):
    """Schema for updating an existing organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class OrganizationResponse(BaseModel):
    """Schema for individual organization response."""

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationDetailResponse(OrganizationResponse):
    """Detailed organization response including member count."""

    member_count: int = Field(default=0, description="Number of active team members")


class TeamMemberResponse(BaseModel):
    """Schema for team member response."""

    id: UUID
    user_id: UUID
    organization_id: UUID
    role: str
    is_active: bool
    joined_at: datetime
    invitation_accepted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeamMemberDetailResponse(TeamMemberResponse):
    """Detailed team member response with user information."""

    username: str = Field(..., description="Username of team member")
    email: str = Field(..., description="Email of team member")


class InviteMemberRequest(BaseModel):
    """Schema for inviting a new team member."""

    email: str = Field(..., description="Email of user to invite")
    role: str = Field(
        default="analyst",
        description="Role to assign to invited member (owner, admin, analyst, viewer)",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of allowed values."""
        allowed_roles = {"owner", "admin", "analyst", "viewer"}
        if v.lower() not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v.lower()


class UpdateMemberRoleRequest(BaseModel):
    """Schema for updating team member role."""

    role: str = Field(
        ...,
        description="New role for team member (owner, admin, analyst, viewer)",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of allowed values."""
        allowed_roles = {"owner", "admin", "analyst", "viewer"}
        if v.lower() not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v.lower()


class RemoveMemberRequest(BaseModel):
    """Schema for removing a team member."""

    reason: Optional[str] = Field(None, description="Optional reason for removal")
