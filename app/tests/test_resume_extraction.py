import asyncio
import json
from pathlib import Path

import fitz

from app.schemas.documents import (
    DocumentFormat,
    DocumentKind,
    FileInput,
    ResumeExtractDebug,
    TextInput,
)
from app.services import document as document_module
from app.services.document import (
    DocumentFileParseError,
    DocumentService,
    InsufficientJobContentError,
    UnsupportedDocumentFormatError,
)


RESUME_TEXT = """
성명: 홍길동
Email: hong@example.com
전화: 010-1234-5678

자기소개
백엔드 개발자로 API 설계와 운영 자동화를 좋아합니다.

경력
핏폴리오 - 백엔드 개발자

프로젝트
채용 공고 크롤러 개선

기술스택
Python, FastAPI, PostgreSQL, Docker

학력
한국대학교 컴퓨터공학과

자격증
정보처리기사

추가 설명
대규모 트래픽 환경에서 REST API를 설계하고 운영 자동화를 구축했습니다.
테스트 자동화, 배포 파이프라인 개선, 장애 대응 문서화 경험이 있습니다.
협업 과정에서는 요구사항을 구조화하고 반복 가능한 개발 프로세스를 만드는 일을 담당했습니다.
"""

PDF_RESUME_TEXT = """
Name: Hong Gil Dong
Email: hong@example.com
Phone: 010-1234-5678

Profile
Backend developer focused on API design and operations automation.

Experience
Fitfolio - Backend Developer

Projects
Recruit crawler improvement

Skills
Python, FastAPI, PostgreSQL, Docker

Education
Korea University Computer Science

Certifications
Engineer Information Processing

Additional
Built reliable REST APIs, automated deployments, and improved incident response documents.
"""


async def fake_resume_structured(text, fallback):
    return fallback


async def fake_irrelevant_resume_structured(text, fallback):
    return ResumeExtractDebug(
        relevant=False,
        failure_reason="이력서가 아닌 안내문입니다.",
        text=text,
    )


def test_resume_text_parse_includes_structured_extract_metadata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(document_module, "_DEBUG_IMAGE_DIR", tmp_path)
    monkeypatch.setattr(document_module, "extract_resume_structured", fake_resume_structured)

    parsed = asyncio.run(
        DocumentService(documents_repository=None).text_to_parsed(  # type: ignore[arg-type]
            TextInput(
                document_type=DocumentKind.RESUME,
                input_type=DocumentFormat.TEXT,
                text=RESUME_TEXT,
            )
        )
    )

    payload = parsed.metadata["resume_extract"]
    debug = ResumeExtractDebug.model_validate(payload)
    assert debug.source == "resume"
    assert debug.name == "홍길동"
    assert debug.email == "hong@example.com"
    assert debug.phone == "010-1234-5678"
    assert "FastAPI" in debug.skills
    assert "application_period" not in payload
    debug_files = list(tmp_path.glob("resume-extract-*.json"))
    assert len(debug_files) == 1
    file_payload = json.loads(debug_files[0].read_text(encoding="utf-8"))
    assert ResumeExtractDebug.model_validate(file_payload) == debug


def test_resume_pdf_parse_includes_structured_extract_metadata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(document_module, "_DEBUG_IMAGE_DIR", tmp_path)
    monkeypatch.setattr(document_module, "extract_resume_structured", fake_resume_structured)

    pdf_path = tmp_path / "resume.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), PDF_RESUME_TEXT)
    doc.save(pdf_path)
    doc.close()

    parsed = asyncio.run(
        DocumentService(documents_repository=None).pdf_to_text(  # type: ignore[arg-type]
            FileInput(
                document_type=DocumentKind.RESUME,
                input_type=DocumentFormat.PDF,
                file_path=str(pdf_path),
                file_name="resume.pdf",
                content_type="application/pdf",
            )
        )
    )

    payload = parsed.metadata["resume_extract"]
    debug = ResumeExtractDebug.model_validate(payload)
    assert debug.email == "hong@example.com"
    assert "Python" in debug.skills
    debug_files = list(tmp_path.glob("resume-extract-*.json"))
    assert len(debug_files) == 1
    file_payload = json.loads(debug_files[0].read_text(encoding="utf-8"))
    assert ResumeExtractDebug.model_validate(file_payload) == debug


def test_invalid_pdf_file_raises_user_friendly_error(tmp_path: Path):
    pdf_path = tmp_path / "not-a-real.pdf"
    pdf_path.write_text("this is not a pdf", encoding="utf-8")

    try:
        asyncio.run(
            DocumentService(documents_repository=None).pdf_to_text(  # type: ignore[arg-type]
                FileInput(
                    document_type=DocumentKind.RESUME,
                    input_type=DocumentFormat.PDF,
                    file_path=str(pdf_path),
                    file_name="not-a-real.pdf",
                    content_type="application/pdf",
                )
            )
        )
    except DocumentFileParseError as exc:
        message = str(exc)
        assert "PDF 파일을 읽지 못했습니다" in message
        assert str(pdf_path) not in message
        assert "FileDataError" not in message
    else:
        raise AssertionError("invalid pdf should fail with DocumentFileParseError")


def test_unsupported_file_format_raises_user_friendly_error():
    try:
        asyncio.run(
            DocumentService(documents_repository=None).parse(  # type: ignore[arg-type]
                FileInput(
                    document_type=DocumentKind.RESUME,
                    input_type=DocumentFormat.IMAGE,
                    file_path="resume.png",
                    file_name="resume.png",
                    content_type="image/png",
                )
            )
        )
    except UnsupportedDocumentFormatError as exc:
        assert "아직 지원하지 않는 파일 형식입니다" in str(exc)
    else:
        raise AssertionError("unsupported file format should fail with user-friendly error")


def test_resume_text_parse_fails_when_llm_says_irrelevant(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(document_module, "_DEBUG_IMAGE_DIR", tmp_path)
    monkeypatch.setattr(document_module, "extract_resume_structured", fake_irrelevant_resume_structured)

    try:
        asyncio.run(
            DocumentService(documents_repository=None).text_to_parsed(  # type: ignore[arg-type]
                TextInput(
                    document_type=DocumentKind.RESUME,
                    input_type=DocumentFormat.TEXT,
                    text=RESUME_TEXT,
                )
            )
        )
    except InsufficientJobContentError as exc:
        assert "이력서가 아닌 안내문입니다." in str(exc)
    else:
        raise AssertionError("irrelevant resume text should fail")
