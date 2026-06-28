import asyncio
from pathlib import Path

import pytest

from app.schemas.documents import DocumentFormat, DocumentKind
from app.services.document import DocumentService


class _FakeUpload:
    def __init__(self, filename: str = "resume.pdf", content_type: str = "application/pdf") -> None:
        self.filename = filename
        self.content_type = content_type


@pytest.mark.asyncio
async def test_request_application_parse_dispatches_resume_and_url_job_concurrently():
    resume_started = asyncio.Event()
    job_started = asyncio.Event()

    class Svc(DocumentService):
        def __init__(self) -> None:
            super().__init__(documents_repository=None)  # type: ignore[arg-type]

        async def save(self, format, file, *, document_type, suffix, max_bytes) -> Path:
            return Path("/tmp/resume.pdf")

        async def request_parse(self, *, document_type, format, file_name, file_path, content_type) -> int:
            resume_started.set()
            await job_started.wait()
            return 11

        async def request_parse_url(self, *, document_type, url) -> int:
            job_started.set()
            await resume_started.wait()
            return 22

    result = await asyncio.wait_for(
        Svc().request_application_parse(
            resume_format=DocumentFormat.PDF,
            resume_file=_FakeUpload(),  # type: ignore[arg-type]
            job_posting_format=DocumentFormat.URL,
            job_posting_url="https://www.wanted.co.kr/wd/366125",
        ),
        timeout=1,
    )

    assert result.resume_document_id == 11
    assert result.job_posting_document_id == 22


@pytest.mark.asyncio
async def test_request_application_parse_saves_resume_and_file_job_concurrently():
    resume_save = asyncio.Event()
    job_save = asyncio.Event()

    class Svc(DocumentService):
        def __init__(self) -> None:
            super().__init__(documents_repository=None)  # type: ignore[arg-type]

        async def save(self, format, file, *, document_type, suffix, max_bytes) -> Path:
            if document_type == DocumentKind.RESUME:
                resume_save.set()
                await job_save.wait()
                return Path("/tmp/resume.pdf")
            job_save.set()
            await resume_save.wait()
            return Path("/tmp/job.pdf")

        async def request_parse(self, *, document_type, format, file_name, file_path, content_type) -> int:
            return 11 if document_type == DocumentKind.RESUME else 22

    result = await asyncio.wait_for(
        Svc().request_application_parse(
            resume_format=DocumentFormat.PDF,
            resume_file=_FakeUpload("resume.pdf"),  # type: ignore[arg-type]
            job_posting_format=DocumentFormat.PDF,
            job_posting_file=_FakeUpload("job.pdf"),  # type: ignore[arg-type]
        ),
        timeout=1,
    )

    assert result.resume_document_id == 11
    assert result.job_posting_document_id == 22
