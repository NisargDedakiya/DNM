"""add plugin marketplace and integration tables

Revision ID: 0009_plugin_marketplace_extensions
Revises: 0008_autonomous_strategy_campaign_intelligence
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_plugin_marketplace_extensions"
down_revision = "0008_autonomous_strategy_campaign_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=True),
    )
    op.create_index("ix_plugins_org_name", "plugins", ["organization_id", "name"], unique=False)
    op.create_index("ix_plugins_org_version", "plugins", ["organization_id", "version"], unique=False)

    op.create_table(
        "plugin_installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plugin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False),
        sa.Column("installed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("installed_at", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_plugin_installations_org_created", "plugin_installations", ["organization_id", "created_at"], unique=False)
    op.create_index("ix_plugin_installations_org_plugin", "plugin_installations", ["organization_id", "plugin_id"], unique=False)

    op.create_table(
        "integration_connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connector_type", sa.String(length=64), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_connector_org_type", "integration_connectors", ["organization_id", "connector_type"], unique=False)
    op.create_index("ix_connector_org_enabled", "integration_connectors", ["organization_id", "enabled"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_connector_org_enabled", table_name="integration_connectors")
    op.drop_index("ix_connector_org_type", table_name="integration_connectors")
    op.drop_table("integration_connectors")

    op.drop_index("ix_plugin_installations_org_plugin", table_name="plugin_installations")
    op.drop_index("ix_plugin_installations_org_created", table_name="plugin_installations")
    op.drop_table("plugin_installations")

    op.drop_index("ix_plugins_org_version", table_name="plugins")
    op.drop_index("ix_plugins_org_name", table_name="plugins")
    op.drop_table("plugins")
