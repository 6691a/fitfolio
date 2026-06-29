"""split job_posting raw_text into document_text and image_text

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "job_posting_profiles",
        sa.Column(
            "document_text",
            sa.Text(),
            nullable=False,
            server_default="",
            comment="문서/페이지/URL 본문에서 추출한 text. 이미지 OCR 텍스트는 포함하지 않는다.",
        ),
    )
    op.add_column(
        "job_posting_profiles",
        sa.Column(
            "image_text",
            sa.Text(),
            nullable=False,
            server_default="",
            comment="채용공고 이미지(OCR)에서 추출한 text. 이미지가 없으면 빈 문자열.",
        ),
    )
    op.execute("UPDATE job_posting_profiles SET document_text = raw_text")
    op.alter_column("job_posting_profiles", "document_text", server_default=None)
    op.drop_column("job_posting_profiles", "raw_text")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "job_posting_profiles",
        sa.Column(
            "raw_text",
            sa.Text(),
            nullable=False,
            server_default="",
            comment="AI/크롤러 DTO가 반환한 채용공고 본문 text. 구조화 JSON 래퍼는 저장하지 않는다.",
        ),
    )
    op.execute(
        "UPDATE job_posting_profiles SET raw_text = TRIM(BOTH E'\\n' FROM document_text || E'\\n\\n' || image_text)"
    )
    op.alter_column("job_posting_profiles", "raw_text", server_default=None)
    op.drop_column("job_posting_profiles", "image_text")
    op.drop_column("job_posting_profiles", "document_text")
