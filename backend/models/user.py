"""
User model for authentication and ownership relationships.
"""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, relationship, mapped_column

from backend.database.base import BaseModel


class User(BaseModel):
    """Application user account."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    programs = relationship(
        "Program",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    scans = relationship("Scan", back_populates="created_by", passive_deletes=True)
    findings = relationship("Finding", back_populates="created_by", passive_deletes=True)
    reports = relationship("Report", back_populates="created_by", passive_deletes=True)