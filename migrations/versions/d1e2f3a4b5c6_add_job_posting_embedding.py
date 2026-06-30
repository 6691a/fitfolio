"""add job_posting_profiles embedding (pgvector) for semantic search

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-06-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_job_posting_profiles_embedding"


def upgrade() -> None:
    """Upgrade schema."""
    # raw SQL로 vector 컬럼 생성(파이썬 pgvector 패키지 의존 없이 — Postgres vector 확장만 사용).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE job_posting_profiles ADD COLUMN embedding vector(768)")
    op.execute(f"CREATE INDEX {_INDEX} ON job_posting_profiles USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
    op.drop_column("job_posting_profiles", "embedding")
