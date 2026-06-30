"""drop job_posting_profiles embedding (search moved to pg_trgm)

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_job_posting_profiles_embedding"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
    op.execute("ALTER TABLE job_posting_profiles DROP COLUMN IF EXISTS embedding")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE job_posting_profiles ADD COLUMN embedding vector(1024)")
    op.execute(f"CREATE INDEX {_INDEX} ON job_posting_profiles USING hnsw (embedding vector_cosine_ops)")
