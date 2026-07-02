"""add title to resume_profiles

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "resume_profiles",
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
            comment="이력서 제목/헤드라인. 예: '3년차 백엔드 개발자 이력서'.",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("resume_profiles", "title")
