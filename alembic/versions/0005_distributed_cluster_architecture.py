"""add distributed cluster worker grid

Revision ID: 0005_distributed_cluster_architecture
Revises: 0004_exposure_timeline_intelligence
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_distributed_cluster_architecture"
down_revision = "0004_exposure_timeline_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'idle'")),
        sa.Column("current_load", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("health_score", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_worker_nodes_region", "worker_nodes", ["region"], unique=False)
    op.create_index("ix_worker_nodes_status", "worker_nodes", ["status"], unique=False)
    op.create_index("ix_worker_nodes_organization_id", "worker_nodes", ["organization_id"], unique=False)

    op.create_table(
        "cluster_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("assigned_worker", postgresql.UUID(as_uuid=True), sa.ForeignKey("worker_nodes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_cluster_jobs_org_status_priority", "cluster_jobs", ["organization_id", "status", "priority"], unique=False)
    op.create_index("ix_cluster_jobs_org_created", "cluster_jobs", ["organization_id", "created_at"], unique=False)
    op.create_index("ix_cluster_jobs_assigned_worker", "cluster_jobs", ["assigned_worker"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cluster_jobs_assigned_worker", table_name="cluster_jobs")
    op.drop_index("ix_cluster_jobs_org_created", table_name="cluster_jobs")
    op.drop_index("ix_cluster_jobs_org_status_priority", table_name="cluster_jobs")
    op.drop_table("cluster_jobs")
    op.drop_index("ix_worker_nodes_organization_id", table_name="worker_nodes")
    op.drop_index("ix_worker_nodes_status", table_name="worker_nodes")
    op.drop_index("ix_worker_nodes_region", table_name="worker_nodes")
    op.drop_table("worker_nodes")
