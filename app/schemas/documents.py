from enum import StrEnum
from typing import Literal, Annotated, Union

from pydantic import Field, BaseModel, HttpUrl


class DocumentFormat(StrEnum):
    PDF = "pdf"
    TEXT = "text"
    IMAGE = "image"
    URL = "url"
    HTML = "html"
    DOCX = "docx"
    PPT = "ppt"


class DocumentKind(StrEnum):
    RESUME = "resume"
    JOB_POSTING = "job_posting"


class EmploymentType(StrEnum):
    """채용 형태(사람인 근무형태 기준 단순화). 판단 불가/해당 없음은 OTHER."""

    FULL_TIME = "정규직"
    CONTRACT = "계약직"
    INTERN = "인턴"
    PART_TIME_JOB = "아르바이트"
    FREELANCE = "프리랜서"
    DISPATCH = "파견직"
    PART_TIME = "파트타임"
    OTHER = "기타"


class Region(StrEnum):
    """근무지 대분류(시/도 17개). 판단 불가/해당 없음은 OTHER."""

    SEOUL = "서울"
    BUSAN = "부산"
    DAEGU = "대구"
    INCHEON = "인천"
    GWANGJU = "광주"
    DAEJEON = "대전"
    ULSAN = "울산"
    SEJONG = "세종"
    GYEONGGI = "경기"
    GANGWON = "강원"
    CHUNGBUK = "충북"
    CHUNGNAM = "충남"
    JEONBUK = "전북"
    JEONNAM = "전남"
    GYEONGBUK = "경북"
    GYEONGNAM = "경남"
    JEJU = "제주"
    OTHER = "기타"


SUPPORTED_MIME_TYPES: dict[DocumentFormat, frozenset[str]] = {
    DocumentFormat.PDF: frozenset({"application/pdf"}),
    DocumentFormat.IMAGE: frozenset({"image/png", "image/jpeg", "image/webp"}),
    DocumentFormat.DOCX: frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
    ),
    DocumentFormat.PPT: frozenset(
        {
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }
    ),
}


class FileInput(BaseModel):
    document_type: DocumentKind
    input_type: Literal[
        DocumentFormat.PDF,
        DocumentFormat.DOCX,
        DocumentFormat.IMAGE,
        DocumentFormat.PPT,
    ]
    file_path: str
    file_name: str
    content_type: str


class TextInput(BaseModel):
    document_type: DocumentKind
    input_type: Literal[DocumentFormat.TEXT]
    text: str


class UrlInput(BaseModel):
    document_type: DocumentKind
    input_type: Literal[DocumentFormat.URL]
    url: HttpUrl


class HtmlInput(BaseModel):
    document_type: DocumentKind
    input_type: Literal[DocumentFormat.HTML]
    html: str


DocumentInput = Annotated[Union[FileInput, TextInput, UrlInput, HtmlInput], Field(discriminator="input_type")]


class ParsedDocument(BaseModel):
    original_input: DocumentInput
    extracted_text: str
    metadata: dict = Field(default_factory=dict)


class DocumentClassification(BaseModel):
    expected_kind: DocumentKind
    detected_kind: DocumentKind | Literal["unknown"]
    is_expected: bool
    confidence: float = Field(ge=0, le=1)
    failure_reason: str | None = None


class JobPostingImage(BaseModel):
    src: str
    alt: str = ""
    text: str | None = None


class JobPosition(BaseModel):
    """한 채용공고 안의 개별 모집부문(포지션). 여러 직무를 하나로 올린 공고를 분리 보존한다."""

    title: str | None = Field(default=None, description="이 포지션의 직무명. 예: 백엔드 개발자, HR 담당자.")
    domain: str | None = Field(default=None, description="정규화된 직군 한 개. 예: 백엔드, 데이터, 인사.")
    tech_tags: list[str] = Field(default_factory=list, description="이 포지션의 정규화 기술 스택 토큰.")
    career_requirement: str | None = Field(default=None, description="이 포지션의 경력 요건.")
    education_requirement: str | None = Field(default=None, description="이 포지션의 학력 요건.")
    responsibilities: list[str] = Field(default_factory=list, description="이 포지션의 주요 업무.")
    qualifications: list[str] = Field(default_factory=list, description="이 포지션의 자격 요건.")
    preferred_qualifications: list[str] = Field(default_factory=list, description="이 포지션의 우대 사항.")


class JobPostingExtractDebug(BaseModel):
    source: str
    relevant: bool = True
    failure_reason: str | None = None
    detail_url: str | None = None
    company_name: str | None = Field(default=None, description="채용 회사명")
    title: str | None = None
    position: str | None = None
    text: str
    work_location: str | None = None
    region: Region | None = Field(default=None, description="근무지 대분류(시/도). 주소를 보고 분류, 모르면 기타")
    employment_type: EmploymentType | None = Field(default=None, description="채용 형태. 모르면 기타")
    career_requirement: str | None = Field(default=None, description="경력 요건. 예: 3년 이상, 신입, 경력 무관")
    education_requirement: str | None = Field(default=None, description="학력 요건. 예: 학력 무관, 대졸 이상")
    domain: str | None = Field(
        default=None,
        description=(
            "정규화된 직군 한 개. 표기가 달라도 같은 직군은 같은 값으로 통일한다. "
            "예: 백엔드, 프론트엔드, 풀스택, 데이터, 머신러닝, 인프라/DevOps, 모바일, 보안, 기획, 디자인. "
            "판단 불가면 비운다."
        ),
    )
    tech_tags: list[str] = Field(
        default_factory=list,
        description="정규화된 핵심 기술 스택 토큰. 예: Python, AWS, Django, Kubernetes. 표기는 공식 명칭으로 통일한다.",
    )
    application_start_date: str | None = None
    application_end_date: str | None = None
    start_date: str | None = Field(
        default=None,
        description="채용 시작 일시. 가능하면 UTC ISO 8601 형식으로 작성한다. 예: 2026-05-31T15:00:00Z",
    )
    end_date: str | None = Field(
        default=None,
        description=(
            "채용 종료 일시. 가능하면 UTC ISO 8601 형식으로 작성한다. "
            "상시채용/채용시 마감/수시채용이면 '상시채용'으로 작성한다."
        ),
    )
    application_method: str | None = None
    timezone: str | None = Field(
        default=None,
        description="채용공고 일시 해석에 사용할 IANA timezone 이름. 예: Asia/Seoul, America/New_York",
    )
    responsibilities: list[str] = Field(default_factory=list, description="주요 업무")
    qualifications: list[str] = Field(default_factory=list, description="자격 요건")
    preferred_qualifications: list[str] = Field(default_factory=list, description="우대 사항")
    benefits: list[str] = Field(default_factory=list, description="혜택 및 복지")
    positions: list[JobPosition] = Field(
        default_factory=list,
        description=(
            "한 공고 안에 모집부문(직무)이 여러 개면 각 포지션을 분리해 채운다. 각 포지션의 업무·자격·기술을 "
            "다른 포지션과 섞지 말고 해당 포지션 것만 담는다. 모집부문이 하나면 원소 1개, 판단 불가면 비운다. "
            "상위 responsibilities/qualifications 등은 공고 전체 요약으로 유지한다."
        ),
    )
    image_urls: list[JobPostingImage] = Field(default_factory=list)
    html: str | None = None
    raw: dict | None = None


class ResumeExtractDebug(BaseModel):
    source: str = "resume"
    relevant: bool = True
    failure_reason: str | None = None
    text: str
    title: str | None = Field(
        default=None,
        description=(
            "이력서 제목/헤드라인. 이력서에 명시된 제목이 있으면 그대로 쓰고, 없으면 직무·경력을 반영해 "
            "간결하게 생성한다. 예: '3년차 백엔드 개발자 이력서', 'AI 서비스 프론트엔드 엔지니어'."
        ),
    )
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    self_introduction: str | None = None
    career_summary: str | None = None
    work_experiences: list[dict | str] = Field(default_factory=list)
    projects: list[dict | str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[dict | str] = Field(default_factory=list)
    certifications: list[dict | str] = Field(default_factory=list)
    links: list[str] = Field(
        default_factory=list,
        description="이력서에 포함된 URL 목록. 포트폴리오·GitHub·블로그·링크드인 등. 예: https://github.com/hong",
    )
    etc: list[dict | str] = Field(
        default_factory=list,
        description=(
            "위 항목(자기소개·경력요약·경력·프로젝트·스킬·학력·자격증·링크) 어디에도 분류되지 않는 "
            "기타 정보를 모은다. 분류 불가한 내용만 넣고, 이미 다른 필드에 담은 값은 중복하지 않는다."
        ),
    )
    image_texts: list[str] = Field(default_factory=list)
    raw_sections: dict = Field(default_factory=dict)


class ParseJobAccepted(BaseModel):
    document_id: int


class ParseApplicationAccepted(BaseModel):
    resume_document_id: int
    job_posting_document_id: int


class ParseStatus(StrEnum):
    PENDING = "pending"
    STARTED = "started"
    RETRY = "retry"
    DONE = "done"
    FAILED = "failed"


class ParseJobStatus(BaseModel):
    document_id: int
    status: ParseStatus
    result: ParsedDocument | None = None
    error: str | None = None
