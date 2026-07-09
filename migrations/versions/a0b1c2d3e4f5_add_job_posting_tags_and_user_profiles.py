"""add normalized tags to job postings and user_profiles aggregate table

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-07-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "f9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "job_posting_profiles",
        sa.Column(
            "domain",
            sa.String(length=255),
            nullable=True,
            comment="정규화된 직군 태그(단일 값). 관심 직군 집계용. 예: 백엔드, 데이터, 프론트엔드.",
        ),
    )
    op.add_column(
        "job_posting_profiles",
        sa.Column(
            "tech_tags",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment="정규화된 핵심 기술 태그 목록. 관심 기술 집계용. 예: Python, AWS, Django.",
        ),
    )
    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
            comment="프로필 소유자(users.id). 사용자당 1행만 가진다.",
        ),
        sa.Column(
            "interest_domains",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment="관심 직군 태그(최근성 가중 상위). 분석한 공고 domain 집계.",
        ),
        sa.Column(
            "interest_tech",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment="관심 기술 태그(최근성 가중 상위). 분석한 공고 tech_tags 집계.",
        ),
        sa.Column(
            "own_skills",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment="사용자 보유 기술(이력서 skills 집계).",
        ),
        sa.Column(
            "experience_months",
            sa.Integer(),
            nullable=True,
            comment="총 경력 개월 수(가장 최근 이력서 기준). 파싱 불가면 NULL.",
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_profiles_id"), "user_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_user_profiles_user_id"), "user_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_profiles_user_id"), table_name="user_profiles")
    op.drop_index(op.f("ix_user_profiles_id"), table_name="user_profiles")
    op.drop_table("user_profiles")
    op.drop_column("job_posting_profiles", "tech_tags")
    op.drop_column("job_posting_profiles", "domain")
