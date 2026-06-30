"""resize job_posting_profiles.embedding to 1024 dims (gemini-embedding-001)

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-06-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_job_posting_profiles_embedding"


def _swap_embedding(dim: int) -> None:
    """embedding 컬럼을 주어진 차원으로 다시 만든다(기존 값은 전부 NULL이라 무손실)."""
    # raw SQL로 vector 컬럼 재생성(파이썬 pgvector 패키지 의존 없이).
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
    op.execute("ALTER TABLE job_posting_profiles DROP COLUMN embedding")
    op.execute(f"ALTER TABLE job_posting_profiles ADD COLUMN embedding vector({dim})")
    op.execute(f"CREATE INDEX {_INDEX} ON job_posting_profiles USING hnsw (embedding vector_cosine_ops)")


def upgrade() -> None:
    """Upgrade schema."""
    _swap_embedding(1024)


def downgrade() -> None:
    """Downgrade schema."""
    _swap_embedding(768)
