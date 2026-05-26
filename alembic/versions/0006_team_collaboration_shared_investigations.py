"""add collaborative investigation workspace tables

Revision ID: 0006_team_collaboration_shared_investigations
Revises: 0005_distributed_cluster_architecture
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_team_collaboration_shared_investigations"
down_revision = "0005_distributed_cluster_architecture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'open'")),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_finding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("findings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("workflow_stage", sa.String(length=32), nullable=False, server_default=sa.text("'open'")),
    )
    op.create_index("ix_investigations_org_status", "investigations", ["organization_id", "status"], unique=False)
    op.create_index("ix_investigations_org_severity", "investigations", ["organization_id", "severity"], unique=False)
    op.create_index("ix_investigations_assigned_to", "investigations", ["assigned_to"], unique=False)
    op.create_index("ix_investigations_source_finding_id", "investigations", ["source_finding_id"], unique=False)

    op.create_table(
        "investigation_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parent_comment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigation_comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_investigation_comments_thread", "investigation_comments", ["investigation_id", "created_at"], unique=False)
    op.create_index("ix_investigation_comments_parent", "investigation_comments", ["parent_comment_id"], unique=False)

    op.create_table(
        "evidence_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(length=2048), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False, server_default=sa.text("'note'")),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("parent_evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_evidence_items_investigation_version", "evidence_items", ["investigation_id", "version"], unique=False)
    op.create_index("ix_evidence_items_parent", "evidence_items", ["parent_evidence_id"], unique=False)

    op.create_table(
        "task_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'assigned'")),
        sa.Column("assigned_at", sa.String(length=64), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("escalation_level", sa.String(length=32), nullable=True),
        sa.Column("escalation_reason", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_task_assignments_investigation_status", "task_assignments", ["investigation_id", "status"], unique=False)
    op.create_index("ix_task_assignments_assignee", "task_assignments", ["assignee_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_task_assignments_assignee", table_name="task_assignments")
    op.drop_index("ix_task_assignments_investigation_status", table_name="task_assignments")
    op.drop_table("task_assignments")
    op.drop_index("ix_evidence_items_parent", table_name="evidence_items")
    op.drop_index("ix_evidence_items_investigation_version", table_name="evidence_items")
    op.drop_table("evidence_items")
    op.drop_index("ix_investigation_comments_parent", table_name="investigation_comments")
    op.drop_index("ix_investigation_comments_thread", table_name="investigation_comments")
    op.drop_table("investigation_comments")
    op.drop_index("ix_investigations_source_finding_id", table_name="investigations")
    op.drop_index("ix_investigations_assigned_to", table_name="investigations")
    op.drop_index("ix_investigations_org_severity", table_name="investigations")
    op.drop_index("ix_investigations_org_status", table_name="investigations")
    op.drop_table("investigations")