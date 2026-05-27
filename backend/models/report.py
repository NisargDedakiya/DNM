"""
Report model for AI-generated or human-generated findings summaries.
"""
from uuid import UUID
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text, Float, Integer, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class Report(BaseModel):
    """Generated report linked to a finding."""

    __tablename__ = "reports"

    finding_id: Mapped[UUID] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(100), nullable=False, default="hackerone")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    vulnerability_type: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    steps_to_reproduce: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    quality_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    improvements: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    platform_submission_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    generated_by_ai: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default="true",
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    finding = relationship("Finding", back_populates="reports")
    created_by = relationship("User", back_populates="reports")
