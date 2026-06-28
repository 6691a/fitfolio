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
    title: str | None = None
    position: str | None = None
    text: str
    work_location: str | None = None
    application_start_date: str | None = None
    application_end_date: str | None = None
    application_method: str | None = None
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
