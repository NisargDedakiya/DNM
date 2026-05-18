"""
Organization model for multi-tenant workspace support.
Organizations are the top-level containers for team collaboration.
"""
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class Organization(BaseModel):
    """
    Organization representing a team workspace.
    
    Organizations provide workspace isolation and team collaboration features.
    Each organization can have multiple team members with different roles and permissions.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    
    members = relationship(
        "TeamMember",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    programs = relationship(
        "Program",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    scans = relationship(
        "Scan",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    findings = relationship(
        "Finding",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    assets = relationship(
        "Asset",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    exposures = relationship(
        "Exposure",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    bugcrowd_programs = relationship(
        "BugcrowdProgram",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_organization_owner_slug", "owner_id", "slug"),
    )
