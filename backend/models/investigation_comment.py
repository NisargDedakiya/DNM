"""
Investigation comment model for threaded collaboration.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class InvestigationComment(BaseModel):
    """Threaded comment attached to an investigation."""

    __tablename__ = "investigation_comments"

    investigation_id: Mapped[UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_comment_id: Mapped[UUID | None] = mapped_column(ForeignKey("investigation_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    investigation = relationship("Investigation", back_populates="comments")
    author = relationship("User")
    parent_comment = relationship("InvestigationComment", remote_side="InvestigationComment.id")

    __table_args__ = (
        Index("ix_investigation_comments_thread", "investigation_id", "created_at"),
    )
