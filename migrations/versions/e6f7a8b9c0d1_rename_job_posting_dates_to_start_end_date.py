"""rename job posting dates to start_date and end_date

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-06-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("job_posting_profiles", sa.Column("start_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_posting_profiles", sa.Column("end_date", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE job_posting_profiles
        SET
            start_date = opening_starts_at,
            end_date = opening_ends_at
        """
    )
    op.drop_column("job_posting_profiles", "opening_ends_at")
    op.drop_column("job_posting_profiles", "opening_starts_at")
    op.drop_column("job_posting_profiles", "deadline")
    op.drop_column("job_posting_profiles", "opening_period")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "job_posting_profiles",
        sa.Column("opening_period", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "job_posting_profiles",
        sa.Column("deadline", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "job_posting_profiles",
        sa.Column("opening_starts_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_posting_profiles",
        sa.Column("opening_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE job_posting_profiles
        SET
            opening_starts_at = start_date,
            opening_ends_at = end_date
        """
    )
    op.drop_column("job_posting_profiles", "end_date")
    op.drop_column("job_posting_profiles", "start_date")
