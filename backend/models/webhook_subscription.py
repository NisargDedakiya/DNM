"""
Webhook subscription ORM model for signed developer integrations.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import BaseModel


class WebhookSubscription(BaseModel):
    __tablename__ = "webhook_subscriptions"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    subscribed_events: Mapped[list | None] = mapped_column(JSON, nullable=True)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)

    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_webhook_subscriptions_org_created", "organization_id", "created_at"),
        Index("ix_webhook_subscriptions_org_endpoint", "organization_id", "endpoint"),
    )
