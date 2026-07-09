"""add user preferences table and analysis feedback column

Revision ID: f9a0b1c2d3e4
Revises: e5f6a7b8c9d0
Create Date: 2026-07-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "fit_analyses",
        sa.Column(
            "feedback",
            sa.JSON(),
            nullable=True,
            comment="User feedback {rating: 0.5-5.0, note: str}. Used to personalize later answers.",
        ),
    )
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("interest_jobs", sa.Text(), nullable=True),
        sa.Column("interest_skills", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_preferences_id"), "user_preferences", ["id"], unique=False)
    op.create_index(op.f("ix_user_preferences_user_id"), "user_preferences", ["user_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_preferences_user_id"), table_name="user_preferences")
    op.drop_index(op.f("ix_user_preferences_id"), table_name="user_preferences")
    op.drop_table("user_preferences")
    op.drop_column("fit_analyses", "feedback")
