"""add job_posting_profiles.search_text (FTS) + GIN index

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-06-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_job_posting_profiles_search_tsv"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "job_posting_profiles",
        sa.Column(
            "search_text",
            sa.Text(),
            nullable=True,
            comment="FTS(전문검색)용 합성 검색 텍스트. build_job_posting_search_text 결과.",
        ),
    )
    op.execute(
        f"CREATE INDEX {_INDEX} ON job_posting_profiles USING gin (to_tsvector('simple', coalesce(search_text, '')))"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
    op.drop_column("job_posting_profiles", "search_text")
