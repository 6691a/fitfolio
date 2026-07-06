"""add interview preparation to fit analyses

Revision ID: e5f6a7b8c9d0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "fit_analyses",
        sa.Column(
            "interview_preparation",
            sa.JSON(),
            nullable=True,
            comment="InterviewPreparationResult serialized JSON generated on demand.",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("fit_analyses", "interview_preparation")
