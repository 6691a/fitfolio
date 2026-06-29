"""structure resume_profiles: add name/email/phone columns and column comments

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-06-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "b9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS = {
    "name": (sa.String(length=255), "지원자 이름. 예: 홍길동."),
    "email": (sa.String(length=255), "지원자 이메일. 예: hong@example.com."),
    "phone": (sa.String(length=50), "지원자 연락처. 예: 010-1234-5678."),
}

_COMMENTS = {
    "document_id": "원본 이력서 문서(documents.id). 문서 1개당 이력서 프로필 1개만 가진다.",
    "document_text": "문서/페이지 본문에서 추출한 text. 이미지 OCR 텍스트는 포함하지 않는다.",
    "image_text": "이력서 이미지(OCR)에서 추출한 text. 이미지가 없으면 빈 문자열.",
    "self_introduction": "자기소개/소개글 본문.",
    "career_summary": "경력 요약. 핵심 경력을 압축한 서술.",
    "work_experiences": "경력 목록. 회사/직무/기간/내용 등.",
    "projects": "프로젝트 목록. 프로젝트명/역할/성과 등.",
    "skills": "보유 기술/스킬 목록. 예: Python, FastAPI.",
    "education": "학력 목록. 학교/전공/학위 등.",
    "certifications": "자격증/수상 목록.",
    "raw_sections": "디버깅/추적용 원본 구조화 DTO. resume_extract 전체를 보관한다.",
}


def upgrade() -> None:
    """Upgrade schema."""
    for column_name, (column_type, comment) in _NEW_COLUMNS.items():
        op.add_column(
            "resume_profiles",
            sa.Column(column_name, column_type, nullable=True, comment=comment),
        )
    for column_name, comment in _COMMENTS.items():
        op.alter_column("resume_profiles", column_name, comment=comment)


def downgrade() -> None:
    """Downgrade schema."""
    for column_name in _COMMENTS:
        op.alter_column("resume_profiles", column_name, comment=None)
    for column_name in _NEW_COLUMNS:
        op.drop_column("resume_profiles", column_name)
