"""
Report model for AI-generated or human-generated findings summaries.
"""
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Text
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
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    finding = relationship("Finding", back_populates="reports")
    created_by = relationship("User", back_populates="reports")
