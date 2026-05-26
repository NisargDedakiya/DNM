"""add autonomous strategy campaign intelligence tables

Revision ID: 0008_autonomous_strategy_campaign_intelligence
Revises: 0007_developer_ecosystem_platform
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_autonomous_strategy_campaign_intelligence"
down_revision = "0007_developer_ecosystem_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hunt_strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("strategy_type", sa.String(length=64), nullable=False),
        sa.Column("target_scope", sa.JSON(), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_hunt_strategies_org_created", "hunt_strategies", ["organization_id", "created_at"], unique=False)
    op.create_index("ix_hunt_strategies_org_type", "hunt_strategies", ["organization_id", "strategy_type"], unique=False)

    op.create_table(
        "recon_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default=sa.text("'pending_approval'")),
        sa.Column("methodology", sa.JSON(), nullable=True),
    )
    op.create_index("ix_recon_campaigns_org_created", "recon_campaigns", ["organization_id", "created_at"], unique=False)
    op.create_index("ix_recon_campaigns_org_status", "recon_campaigns", ["organization_id", "status"], unique=False)

    op.create_table(
        "strategy_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("methodology_pattern", sa.JSON(), nullable=True),
        sa.Column("success_score", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_strategy_memory_org_created", "strategy_memory", ["organization_id", "created_at"], unique=False)
    op.create_index("ix_strategy_memory_org_success", "strategy_memory", ["organization_id", "success_score"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_strategy_memory_org_success", table_name="strategy_memory")
    op.drop_index("ix_strategy_memory_org_created", table_name="strategy_memory")
    op.drop_table("strategy_memory")

    op.drop_index("ix_recon_campaigns_org_status", table_name="recon_campaigns")
    op.drop_index("ix_recon_campaigns_org_created", table_name="recon_campaigns")
    op.drop_table("recon_campaigns")

    op.drop_index("ix_hunt_strategies_org_type", table_name="hunt_strategies")
    op.drop_index("ix_hunt_strategies_org_created", table_name="hunt_strategies")
    op.drop_table("hunt_strategies")
