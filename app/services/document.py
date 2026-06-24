import uuid
from pathlib import Path
from typing import cast

import aiofiles
import fitz
import trafilatura
from fastapi import HTTPException, UploadFile, status
from playwright.async_api import async_playwright

from app.config.settings import settings
from app.repositories.documents import DocumentsRepository
from app.schemas.documents import (
    SUPPORTED_MIME_TYPES,
    DocumentFormat,
    DocumentInput,
    DocumentKind,
    FileInput,
    ParsedDocument,
    UrlInput,
)
from app.security.job_domains import is_allowed_job_domain

_UPLOAD_SUBDIRS: dict[DocumentKind, str] = {
    DocumentKind.RESUME: "resumes",
    DocumentKind.JOB_POSTING: "job_postings",
}

_MIN_EXTRACTED_CHARS = 200
_MAX_EXTRACTED_CHARS = 80_000


class BlockedJobUrlError(Exception):
    pass


class InsufficientJobContentError(Exception):
    pass


class DocumentService:
    _CHUNK_SIZE = 1024 * 1024

    def __init__(self, documents_repository: DocumentsRepository) -> None:
        self._documents_repository = documents_repository

    async def save(
        self,
        format: DocumentFormat,
        file: UploadFile,
        *,
        document_type: DocumentKind,
        suffix: str,
        max_bytes: int,
    ) -> Path:
        if file.content_type not in SUPPORTED_MIME_TYPES.get(format, frozenset()):
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "지원하지 않는 파일 형식입니다")

        stored_dir = settings.UPLOAD_DIR / _UPLOAD_SUBDIRS[document_type]
        stored_dir.mkdir(parents=True, exist_ok=True)
        stored_path = stored_dir / f"{uuid.uuid4()}{suffix}"
        size = 0

        try:
            async with aiofiles.open(stored_path, "wb") as out_file:
                while chunk := await file.read(self._CHUNK_SIZE):
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "파일이 너무 큽니다")
                    await out_file.write(chunk)
        except HTTPException:
            stored_path.unlink(missing_ok=True)
            raise

        return stored_path

    async def request_parse(
        self,
        *,
        document_type: DocumentKind,
        format: DocumentFormat,
        file_name: str,
        file_path: str,
        content_type: str,
    ) -> int:
        from app.tasks.documents import task_parse_document

        record = await self._documents_repository.create(
            document_type=document_type,
            format=format,
            file_name=file_name,
            file_path=file_path,
            content_type=content_type,
        )
        task_parse_document.delay(record.id)
        return record.id

    async def request_parse_url(self, *, document_type: DocumentKind, url: str) -> int:
        from app.tasks.documents import task_parse_document

        record = await self._documents_repository.create(
            document_type=document_type,
            format=DocumentFormat.URL,
            source_url=url,
        )
        task_parse_document.delay(record.id)
        return record.id

    async def parse(self, input: DocumentInput) -> ParsedDocument:
        match input.input_type:
            case DocumentFormat.PDF:
                return self.pdf_to_text(input)
            case DocumentFormat.URL:
                return await self.url_to_text(input)
            # case DocumentFormat.TEXT:
            #     return ParsedDocument()
            # case DocumentFormat.IMAGE:
            #     return self.image_to_text(input)
            # case DocumentFormat.HTML:
            #     return self.html_to_text(input)
            # case DocumentFormat.DOCX:
            #     return self.docx_to_text(input)
            # case DocumentFormat.PPT:
            #     return self.ppt_to_text(input)

        raise ValueError(f"Unsupported input type: {input.input_type}")

    def pdf_to_text(self, input: FileInput) -> ParsedDocument:
        with fitz.open(input.file_path) as doc:
            pages = [cast(str, page.get_text("text")) for page in doc]

        return ParsedDocument(
            original_input=input,
            extracted_text="\n\n".join(pages),
            metadata={"page_count": len(pages)},
        )

    async def url_to_text(self, input: UrlInput) -> ParsedDocument:
        url = str(input.url)
        if not is_allowed_job_domain(url):
            raise BlockedJobUrlError(f"허용되지 않은 도메인입니다: {url}")

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=15_000)
                if not is_allowed_job_domain(page.url):
                    raise BlockedJobUrlError(f"허용되지 않은 도메인으로 이동했습니다: {page.url}")
                html = await page.content()
            finally:
                await browser.close()

        return await self.html_to_text(html, input)

    async def image_to_text(self, input: FileInput) -> ParsedDocument:
        raise NotImplementedError

    async def html_to_text(self, html: str, input: UrlInput) -> ParsedDocument:
        text = (trafilatura.extract(html) or "").strip()
        if len(text) < _MIN_EXTRACTED_CHARS:
            raise InsufficientJobContentError(
                "이 URL에서 텍스트를 충분히 추출하지 못했습니다. 채용 공고 본문을 직접 복사해 붙여주세요."
            )

        truncated = text[:_MAX_EXTRACTED_CHARS]

        return ParsedDocument(
            original_input=input,
            extracted_text=truncated,
            metadata={"source_url": str(input.url), "char_count": len(truncated)},
        )
