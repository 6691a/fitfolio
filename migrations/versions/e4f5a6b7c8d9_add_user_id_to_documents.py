"""add user_id to documents

Revision ID: e4f5a6b7c8d9
Revises: d4e5f6a7b8c0
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("documents", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_documents_user_id_users"),
        "documents",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("fk_documents_user_id_users"), "documents", type_="foreignkey")
    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_column("documents", "user_id")
