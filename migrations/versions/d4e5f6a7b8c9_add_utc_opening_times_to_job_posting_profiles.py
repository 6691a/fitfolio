"""add utc opening times to job posting profiles

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-06-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "job_posting_profiles",
        sa.Column("opening_starts_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_posting_profiles",
        sa.Column("opening_ends_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("job_posting_profiles", "opening_ends_at")
    op.drop_column("job_posting_profiles", "opening_starts_at")
