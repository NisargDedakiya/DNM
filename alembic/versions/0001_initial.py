"""Initial models migration

Revision ID: 0001_initial
Revises: 
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables from SQLAlchemy metadata.

    This uses SQLAlchemy metadata to create tables. It requires the database
    configured in alembic.ini to be reachable.
    """
    bind = op.get_bind()
    # Use SQLAlchemy Core connection to run metadata.create_all
    from backend.database.base import Base

    bind.run_sync(lambda connection: Base.metadata.create_all(connection))


def downgrade() -> None:
    """Drop all tables created in upgrade."""
    bind = op.get_bind()
    from backend.database.base import Base

    bind.run_sync(lambda connection: Base.metadata.drop_all(connection))
