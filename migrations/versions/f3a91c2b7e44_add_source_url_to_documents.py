"""add source_url to documents, make file fields nullable

Revision ID: f3a91c2b7e44
Revises: 0972cb763d65
Create Date: 2026-06-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a91c2b7e44"
down_revision: Union[str, Sequence[str], None] = "0972cb763d65"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("documents", sa.Column("source_url", sa.String(length=2048), nullable=True))
    op.alter_column("documents", "file_name", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("documents", "file_path", existing_type=sa.String(length=500), nullable=True)
    op.alter_column("documents", "content_type", existing_type=sa.String(length=100), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("documents", "content_type", existing_type=sa.String(length=100), nullable=False)
    op.alter_column("documents", "file_path", existing_type=sa.String(length=500), nullable=False)
    op.alter_column("documents", "file_name", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("documents", "source_url")
