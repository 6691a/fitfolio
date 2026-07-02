"""add links and etc to resume_profiles

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "resume_profiles",
        sa.Column(
            "links",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment="이력서에 포함된 URL 목록. 포트폴리오·GitHub·블로그·링크드인 등.",
        ),
    )
    op.add_column(
        "resume_profiles",
        sa.Column(
            "etc",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment="다른 항목으로 분류되지 않는 기타 정보 목록.",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("resume_profiles", "etc")
    op.drop_column("resume_profiles", "links")
