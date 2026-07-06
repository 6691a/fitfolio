"""add deleted_at to fit analyses

Revision ID: d4e5f6a7b8c0
Revises: c3d4e5f6a7b8
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c0"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("fit_analyses", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_fit_analyses_deleted_at"), "fit_analyses", ["deleted_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_fit_analyses_deleted_at"), table_name="fit_analyses")
    op.drop_column("fit_analyses", "deleted_at")
