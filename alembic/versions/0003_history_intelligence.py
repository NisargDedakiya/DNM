"""create history intelligence tables

Revision ID: 0003_history_intelligence
Revises: 0002_assets_endpoints_technologies
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0003_history_intelligence"
down_revision = "0002_assets_endpoints_technologies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hunt_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_type", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_hunt_memory_org_type_created", "hunt_memory", ["organization_id", "memory_type", "created_at"], unique=False)

    op.create_table(
        "risk_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("summary", sa.Text(), nullable=False),
    )
    op.create_index("ix_risk_snapshots_org_created", "risk_snapshots", ["organization_id", "created_at"], unique=False)
    op.create_index("ix_risk_snapshots_org_score", "risk_snapshots", ["organization_id", "risk_score"], unique=False)

    op.create_table(
        "exposure_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_exposure_events_org_asset_created", "exposure_events", ["organization_id", "asset", "created_at"], unique=False)
    op.create_index("ix_exposure_events_org_event_created", "exposure_events", ["organization_id", "event_type", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_exposure_events_org_event_created", table_name="exposure_events")
    op.drop_index("ix_exposure_events_org_asset_created", table_name="exposure_events")
    op.drop_table("exposure_events")

    op.drop_index("ix_risk_snapshots_org_score", table_name="risk_snapshots")
    op.drop_index("ix_risk_snapshots_org_created", table_name="risk_snapshots")
    op.drop_table("risk_snapshots")

    op.drop_index("ix_hunt_memory_org_type_created", table_name="hunt_memory")
    op.drop_table("hunt_memory")

