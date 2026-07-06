"""create fit analyses table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUS_VALUES = "'pending', 'started', 'retry', 'done', 'failed'"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "fit_analyses",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("resume_document_id", sa.Integer(), nullable=False),
        sa.Column("job_posting_document_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_posting_document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"status IN ({_STATUS_VALUES})", name="fit_analysis_status"),
    )
    op.create_index(op.f("ix_fit_analyses_id"), "fit_analyses", ["id"], unique=False)
    op.create_index(op.f("ix_fit_analyses_user_id"), "fit_analyses", ["user_id"], unique=False)
    op.create_index(op.f("ix_fit_analyses_resume_document_id"), "fit_analyses", ["resume_document_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_fit_analyses_resume_document_id"), table_name="fit_analyses")
    op.drop_index(op.f("ix_fit_analyses_user_id"), table_name="fit_analyses")
    op.drop_index(op.f("ix_fit_analyses_id"), table_name="fit_analyses")
    op.drop_table("fit_analyses")
