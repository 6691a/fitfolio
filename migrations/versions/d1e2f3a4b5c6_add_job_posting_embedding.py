"""add job_posting_profiles embedding (pgvector) for semantic search

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-06-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_job_posting_profiles_embedding"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "job_posting_profiles",
        sa.Column(
            "embedding",
            Vector(768),
            nullable=True,
            comment="의미 검색용 임베딩 벡터(text-embedding-004, 768d).",
        ),
    )
    op.execute(f"CREATE INDEX {_INDEX} ON job_posting_profiles USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
    op.drop_column("job_posting_profiles", "embedding")
