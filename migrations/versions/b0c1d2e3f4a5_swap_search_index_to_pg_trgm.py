"""swap job_posting_profiles search index from FTS(tsvector) to pg_trgm

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-06-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FTS_INDEX = "ix_job_posting_profiles_search_tsv"
_TRGM_INDEX = "ix_job_posting_profiles_search_trgm"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(f"DROP INDEX IF EXISTS {_FTS_INDEX}")
    op.execute(f"CREATE INDEX {_TRGM_INDEX} ON job_posting_profiles USING gin (search_text gin_trgm_ops)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DROP INDEX IF EXISTS {_TRGM_INDEX}")
    op.execute(
        f"CREATE INDEX {_FTS_INDEX} ON job_posting_profiles "
        "USING gin (to_tsvector('simple', coalesce(search_text, '')))"
    )
