"""add job posting profile column comments

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-06-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COMMENTS = {
    "document_id": "원본 채용공고 문서(documents.id). 문서 1개당 채용공고 프로필 1개만 가진다.",
    "raw_text": "AI/크롤러 DTO가 반환한 채용공고 본문 text. 구조화 JSON 래퍼는 저장하지 않는다.",
    "company_name": "채용 회사명. 예: 마인즈그라운드(주), 무신사.",
    "title": "채용공고 제목 또는 포지션명. 예: 백엔드 개발자 채용.",
    "location": "근무지 주소 또는 지역. 예: 서울 서초구.",
    "employment_type": "고용 형태. 예: 정규직, 계약직, 인턴, 수습 포함 여부.",
    "career_requirement": "경력 요건. 예: 신입, 3년 이상, 경력 무관.",
    "education_requirement": "학력 요건. 예: 학력 무관, 대졸 이상.",
    "start_date": "채용 시작 일시. UTC timezone-aware datetime으로 저장한다.",
    "end_date": "채용 종료 일시. UTC timezone-aware datetime으로 저장하며 상시채용은 9999-12-31 23:59:59Z.",
    "responsibilities": "주요 업무 목록. 채용공고의 담당 업무/Role 항목.",
    "qualifications": "필수 자격 요건 목록. 지원자가 반드시 충족해야 하는 조건.",
    "preferred_qualifications": "우대 사항 목록. 있으면 좋은 경험/기술/조건.",
    "benefits": "복지 및 혜택 목록. 보상, 장비, 휴가, 교육비 등.",
    "source_url": "채용공고 원본 URL. URL 입력/크롤링 문서일 때 사용.",
    "raw_sections": "디버깅/추적용 원본 구조화 DTO. job_posting_extract 전체를 보관한다.",
}


def upgrade() -> None:
    """Upgrade schema."""
    for column_name, comment in _COMMENTS.items():
        op.alter_column("job_posting_profiles", column_name, comment=comment)


def downgrade() -> None:
    """Downgrade schema."""
    for column_name in _COMMENTS:
        op.alter_column("job_posting_profiles", column_name, comment=None)
