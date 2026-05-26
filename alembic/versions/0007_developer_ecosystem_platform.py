"""add developer ecosystem platform tables

Revision ID: 0007_developer_ecosystem_platform
Revises: 0006_team_collaboration_shared_investigations
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_developer_ecosystem_platform"
down_revision = "0006_team_collaboration_shared_investigations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=True),
        sa.Column("rate_limit", sa.JSON(), nullable=True),
    )
    op.create_index("ix_api_keys_org_created", "api_keys", ["organization_id", "created_at"], unique=False)
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(length=2048), nullable=False),
        sa.Column("subscribed_events", sa.JSON(), nullable=True),
        sa.Column("secret", sa.String(length=255), nullable=False),
    )
    op.create_index("ix_webhook_subscriptions_org_created", "webhook_subscriptions", ["organization_id", "created_at"], unique=False)
    op.create_index("ix_webhook_subscriptions_org_endpoint", "webhook_subscriptions", ["organization_id", "endpoint"], unique=False)

    op.create_table(
        "developer_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usage_stats", sa.JSON(), nullable=True),
    )
    op.create_index("ix_developer_apps_org_created", "developer_applications", ["organization_id", "created_at"], unique=False)
    op.create_index("ix_developer_apps_org_name", "developer_applications", ["organization_id", "name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_developer_apps_org_name", table_name="developer_applications")
    op.drop_index("ix_developer_apps_org_created", table_name="developer_applications")
    op.drop_table("developer_applications")

    op.drop_index("ix_webhook_subscriptions_org_endpoint", table_name="webhook_subscriptions")
    op.drop_index("ix_webhook_subscriptions_org_created", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")

    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_index("ix_api_keys_org_created", table_name="api_keys")
    op.drop_table("api_keys")
