from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel, enum_column
from app.schemas.documents import EmploymentType, Region


class ResumeProfile(BaseModel):
    __tablename__ = "resume_profiles"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        comment="원본 이력서 문서(documents.id). 문서 1개당 이력서 프로필 1개만 가진다.",
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        comment="이력서를 업로드한 사용자(users.id). 이력서 목록을 사용자별로 필터링한다.",
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
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="이력서 제목/헤드라인. 예: '3년차 백엔드 개발자 이력서'.",
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
    links: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="이력서에 포함된 URL 목록. 포트폴리오·GitHub·블로그·링크드인 등.",
    )
    etc: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="다른 항목으로 분류되지 않는 기타 정보 목록.",
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
        comment="근무지 상세 주소(표시용). 예: 서울 서초구 남부순환로.",
    )
    region: Mapped[Region | None] = mapped_column(
        enum_column(Region, "region"),
        nullable=True,
        comment="근무지 대분류(시/도 17개 + 기타). 검색/필터용.",
    )
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        enum_column(EmploymentType, "employment_type"),
        nullable=True,
        comment="채용 형태 enum(정규직/계약직/인턴/아르바이트/프리랜서/파견직/파트타임/기타).",
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
    domain: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="정규화된 직군 태그(단일 값). 관심 직군 집계용. 예: 백엔드, 데이터, 프론트엔드.",
    )
    tech_tags: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="정규화된 핵심 기술 태그 목록. 관심 기술 집계용. 예: Python, AWS, Django.",
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
    positions: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="공고 안의 모집부문(포지션) 목록. 여러 직무를 하나로 올린 공고를 분리 보존한다. 적합도 분석은 이력서에 가장 맞는 포지션을 자동 선택한다.",
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
    search_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="FTS(전문검색)용 합성 검색 텍스트. build_job_posting_search_text 결과.",
    )


class UserProfile(BaseModel):
    """분석 이력에서 집계한 사용자 요약 프로필(사용자당 1행).

    원천이 아니라 재생성 가능한 물질화 뷰(캐시)다. 분석 완료 시마다 최근 분석 전체에서
    재계산해 upsert하며(멱등), 다음 분석의 개인화와 관심 설정 프리필의 자동 제안값으로 쓴다.
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        comment="프로필 소유자(users.id). 사용자당 1행만 가진다.",
    )
    interest_domains: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="관심 직군 태그(최근성 가중 상위). 분석한 공고 domain 집계.",
    )
    interest_tech: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="관심 기술 태그(최근성 가중 상위). 분석한 공고 tech_tags 집계.",
    )
    own_skills: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="사용자 보유 기술(이력서 skills 집계).",
    )
    experience_months: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="총 경력 개월 수(가장 최근 이력서 기준). 파싱 불가면 NULL.",
    )
