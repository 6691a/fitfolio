"""convert employment_type to enum and add region enum to job_posting_profiles

Revision ID: d2e3f4a5b6c7
Revises: b0c1d2e3f4a5
Create Date: 2026-06-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EMPLOYMENT_TYPES = ("정규직", "계약직", "인턴", "아르바이트", "프리랜서", "파견직", "파트타임", "기타")
_REGIONS = (
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
    "기타",
)

# 기존 location(상세주소) 접두사 → region 대분류 매핑(자치도 풀네임 별칭 포함).
_REGION_PREFIXES = {
    "서울": ("서울",),
    "부산": ("부산",),
    "대구": ("대구",),
    "인천": ("인천",),
    "광주": ("광주",),
    "대전": ("대전",),
    "울산": ("울산",),
    "세종": ("세종",),
    "경기": ("경기",),
    "강원": ("강원",),
    "제주": ("제주",),
    "충북": ("충북", "충청북도"),
    "충남": ("충남", "충청남도"),
    "전북": ("전북", "전라북도"),
    "전남": ("전남", "전라남도"),
    "경북": ("경북", "경상북도"),
    "경남": ("경남", "경상남도"),
}


def _in_clause(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    """Upgrade schema."""
    # 1) 기존 employment_type 자유 텍스트 → enum 값으로 정리(비매칭은 기타).
    op.execute(
        """
        UPDATE job_posting_profiles SET employment_type = CASE
            WHEN employment_type IS NULL THEN NULL
            WHEN employment_type LIKE '%정규%' THEN '정규직'
            WHEN employment_type LIKE '%계약%' THEN '계약직'
            WHEN employment_type LIKE '%인턴%' THEN '인턴'
            WHEN employment_type LIKE '%아르바이트%' OR employment_type LIKE '%알바%' THEN '아르바이트'
            WHEN employment_type LIKE '%프리%' THEN '프리랜서'
            WHEN employment_type LIKE '%파견%' THEN '파견직'
            WHEN employment_type LIKE '%파트%' OR employment_type LIKE '%시간제%' THEN '파트타임'
            ELSE '기타'
        END
        """
    )
    op.alter_column(
        "job_posting_profiles",
        "employment_type",
        existing_type=sa.String(length=100),
        type_=sa.String(length=20),
    )
    op.create_check_constraint(
        "ck_job_posting_profiles_employment_type",
        "job_posting_profiles",
        f"employment_type IS NULL OR employment_type IN ({_in_clause(_EMPLOYMENT_TYPES)})",
    )

    # 2) region 컬럼 추가 + 기존 location 접두사에서 대분류 추론.
    op.add_column(
        "job_posting_profiles",
        sa.Column(
            "region", sa.String(length=20), nullable=True, comment="근무지 대분류(시/도 17개 + 기타). 검색/필터용."
        ),
    )
    region_case_lines = []
    for region, prefixes in _REGION_PREFIXES.items():
        conditions = " OR ".join(f"location LIKE '{prefix}%'" for prefix in prefixes)
        region_case_lines.append(f"            WHEN {conditions} THEN '{region}'")
    region_cases = "\n".join(region_case_lines)
    op.execute(
        f"""
        UPDATE job_posting_profiles SET region = CASE
{region_cases}
            ELSE NULL
        END
        WHERE location IS NOT NULL
        """
    )
    op.create_check_constraint(
        "ck_job_posting_profiles_region",
        "job_posting_profiles",
        f"region IS NULL OR region IN ({_in_clause(_REGIONS)})",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_job_posting_profiles_region", "job_posting_profiles", type_="check")
    op.drop_column("job_posting_profiles", "region")
    op.drop_constraint("ck_job_posting_profiles_employment_type", "job_posting_profiles", type_="check")
    op.alter_column(
        "job_posting_profiles",
        "employment_type",
        existing_type=sa.String(length=20),
        type_=sa.String(length=100),
    )
