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
