"""
Program model representing a bug bounty program or target scope.
"""
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class Program(BaseModel):
    """Bug bounty program scope and metadata."""

    __tablename__ = "programs"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    handle: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    is_private: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    scope_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    owner = relationship("User", back_populates="programs")
    organization = relationship("Organization", back_populates="programs")
    scans = relationship(
        "Scan",
        back_populates="program",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    findings = relationship(
        "Finding",
        back_populates="program",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_program_organization", "organization_id"),
    )
