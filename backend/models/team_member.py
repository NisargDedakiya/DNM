"""
Team member model for organization membership and RBAC.
Tracks team members, their roles, and invitation status.
"""
from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class MemberRole(str, Enum):
    """Team member roles for RBAC."""

    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class TeamMember(BaseModel):
    """
    Team member representing a user's membership in an organization.
    
    Supports multi-level RBAC with four role tiers:
    - owner: Full control, organization management
    - admin: Administrative functions, member management
    - analyst: Can run scans, manage findings
    - viewer: Read-only access to findings and scans
    """

    __tablename__ = "team_members"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MemberRole.VIEWER,
        index=True,
    )
    
    # Invitation tracking
    invited_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    invitation_accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    invited_by_user = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        Index("idx_org_member_unique", "organization_id", "user_id", unique=True),
        Index("idx_org_member_active", "organization_id", "is_active"),
    )
