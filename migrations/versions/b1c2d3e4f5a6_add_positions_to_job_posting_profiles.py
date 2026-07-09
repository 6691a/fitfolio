"""add positions array to job_posting_profiles

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-07-08 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "job_posting_profiles",
        sa.Column(
            "positions",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment=(
                "공고 안의 모집부문(포지션) 목록. 여러 직무를 하나로 올린 공고를 분리 보존한다. "
                "적합도 분석은 이력서에 가장 맞는 포지션을 자동 선택한다."
            ),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("job_posting_profiles", "positions")
