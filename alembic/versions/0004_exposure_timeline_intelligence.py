"""create exposure timeline intelligence tables

Revision ID: 0004_exposure_timeline_intelligence
Revises: 0003_history_intelligence
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_exposure_timeline_intelligence"
down_revision = "0003_history_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exposure_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset", sa.String(length=255), nullable=False),
        sa.Column("exposure_state", sa.JSON(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
    )
    op.create_index("ix_exposure_snapshots_org_asset_created", "exposure_snapshots", ["organization_id", "asset", "created_at"], unique=False)
    op.create_index("ix_exposure_snapshots_org_score", "exposure_snapshots", ["organization_id", "risk_score"], unique=False)

    op.create_table(
        "drift_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset", sa.String(length=255), nullable=False),
        sa.Column("drift_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
    )
    op.create_index("ix_drift_events_org_asset_created", "drift_events", ["organization_id", "asset", "created_at"], unique=False)
    op.create_index("ix_drift_events_org_type_created", "drift_events", ["organization_id", "drift_type", "created_at"], unique=False)

    op.create_table(
        "risk_evolution_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset", sa.String(length=255), nullable=False),
        sa.Column("previous_risk", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("current_risk", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("summary", sa.Text(), nullable=False),
    )
    op.create_index("ix_risk_evolution_org_asset_created", "risk_evolution_events", ["organization_id", "asset", "created_at"], unique=False)
    op.create_index("ix_risk_evolution_org_risk_created", "risk_evolution_events", ["organization_id", "current_risk", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_risk_evolution_org_risk_created", table_name="risk_evolution_events")
    op.drop_index("ix_risk_evolution_org_asset_created", table_name="risk_evolution_events")
    op.drop_table("risk_evolution_events")

    op.drop_index("ix_drift_events_org_type_created", table_name="drift_events")
    op.drop_index("ix_drift_events_org_asset_created", table_name="drift_events")
    op.drop_table("drift_events")

    op.drop_index("ix_exposure_snapshots_org_score", table_name="exposure_snapshots")
    op.drop_index("ix_exposure_snapshots_org_asset_created", table_name="exposure_snapshots")
    op.drop_table("exposure_snapshots")

