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
    employment_type: str | None = Field(default=None, description="고용 형태. 예: 정규직, 계약직, 인턴")
    career_requirement: str | None = Field(default=None, description="경력 요건. 예: 3년 이상, 신입, 경력 무관")
    education_requirement: str | None = Field(default=None, description="학력 요건. 예: 학력 무관, 대졸 이상")
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
    image_urls: list[JobPostingImage] = Field(default_factory=list)
    html: str | None = None
    raw: dict | None = None


class ResumeExtractDebug(BaseModel):
    source: str = "resume"
    relevant: bool = True
    failure_reason: str | None = None
    text: str
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
