from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.ai.embeddings import EMBEDDING_DIM
from app.database.base import BaseModel


class ResumeProfile(BaseModel):
    __tablename__ = "resume_profiles"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        comment="원본 이력서 문서(documents.id). 문서 1개당 이력서 프로필 1개만 가진다.",
    )
    document_text: Mapped[str] = mapped_column(
        Text,
        comment="문서/페이지 본문에서 추출한 text. 이미지 OCR 텍스트는 포함하지 않는다.",
    )
    image_text: Mapped[str] = mapped_column(
        Text,
        default="",
        comment="이력서 이미지(OCR)에서 추출한 text. 이미지가 없으면 빈 문자열.",
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="지원자 이름. 예: 홍길동.",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="지원자 이메일. 예: hong@example.com.",
    )
    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="지원자 연락처. 예: 010-1234-5678.",
    )
    self_introduction: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="자기소개/소개글 본문.",
    )
    career_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="경력 요약. 핵심 경력을 압축한 서술.",
    )
    work_experiences: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="경력 목록. 회사/직무/기간/내용 등.",
    )
    projects: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="프로젝트 목록. 프로젝트명/역할/성과 등.",
    )
    skills: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="보유 기술/스킬 목록. 예: Python, FastAPI.",
    )
    education: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="학력 목록. 학교/전공/학위 등.",
    )
    certifications: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="자격증/수상 목록.",
    )
    raw_sections: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="디버깅/추적용 원본 구조화 DTO. resume_extract 전체를 보관한다.",
    )


class JobPostingProfile(BaseModel):
    """AI가 채용공고 DTO로 구조화한 값을 저장하는 프로필 테이블."""

    __tablename__ = "job_posting_profiles"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        comment="원본 채용공고 문서(documents.id). 문서 1개당 채용공고 프로필 1개만 가진다.",
    )
    document_text: Mapped[str] = mapped_column(
        Text,
        comment="문서/페이지/URL 본문에서 추출한 text. 이미지 OCR 텍스트는 포함하지 않는다.",
    )
    image_text: Mapped[str] = mapped_column(
        Text,
        default="",
        comment="채용공고 이미지(OCR)에서 추출한 text. 이미지가 없으면 빈 문자열.",
    )
    company_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="채용 회사명. 예: 마인즈그라운드(주), 무신사.",
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="채용공고 제목 또는 포지션명. 예: 백엔드 개발자 채용.",
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="근무지 주소 또는 지역. 예: 서울 서초구.",
    )
    employment_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="고용 형태. 예: 정규직, 계약직, 인턴, 수습 포함 여부.",
    )
    career_requirement: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="경력 요건. 예: 신입, 3년 이상, 경력 무관.",
    )
    education_requirement: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="학력 요건. 예: 학력 무관, 대졸 이상.",
    )
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="채용 시작 일시. UTC timezone-aware datetime으로 저장한다.",
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="채용 종료 일시. UTC timezone-aware datetime으로 저장하며 상시채용은 9999-12-31 23:59:59Z.",
    )
    responsibilities: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="주요 업무 목록. 채용공고의 담당 업무/Role 항목.",
    )
    qualifications: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="필수 자격 요건 목록. 지원자가 반드시 충족해야 하는 조건.",
    )
    preferred_qualifications: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="우대 사항 목록. 있으면 좋은 경험/기술/조건.",
    )
    benefits: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="복지 및 혜택 목록. 보상, 장비, 휴가, 교육비 등.",
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="채용공고 원본 URL. URL 입력/크롤링 문서일 때 사용.",
    )
    raw_sections: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="디버깅/추적용 원본 구조화 DTO. job_posting_extract 전체를 보관한다.",
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM),
        nullable=True,
        comment="의미 검색용 임베딩 벡터(gemini-embedding-001).",
    )
