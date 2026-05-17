"""
Asset model: persistent inventory of hosts discovered by recon.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Boolean, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class Asset(BaseModel):
    __tablename__ = "assets"

    program_id: Mapped[UUID] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    is_alive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    organization = relationship("Organization", back_populates="assets")
    endpoints = relationship("Endpoint", back_populates="asset", cascade="all, delete-orphan", passive_deletes=True)
    technologies = relationship("Technology", back_populates="asset", cascade="all, delete-orphan", passive_deletes=True)
    exposures = relationship("Exposure", back_populates="asset", cascade="all, delete-orphan", passive_deletes=True)
    fingerprint = relationship("AssetFingerprint", back_populates="asset", cascade="all, delete-orphan", passive_deletes=True, uselist=False)

    __table_args__ = (
        Index("ix_assets_program_hostname", "program_id", "hostname", unique=False),
        Index("ix_assets_organization", "organization_id"),
    )
