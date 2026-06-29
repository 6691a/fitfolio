import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.documents import DocumentFormat, ParseApplicationAccepted


@pytest.mark.asyncio
async def test_parse_endpoint_delegates_to_service():
    class FakeDocumentService:
        async def request_application_parse(self, **kwargs):
            assert kwargs["resume_format"] == DocumentFormat.PDF
            assert kwargs["job_posting_format"] == DocumentFormat.URL
            return ParseApplicationAccepted(resume_document_id=11, job_posting_document_id=22)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # pyrefly: ignore [missing-attribute]
        with app.container.document_service.override(FakeDocumentService()):
            response = await client.post(
                "/documents/parse",
                data={
                    "resume_format": DocumentFormat.PDF.value,
                    "job_posting_format": DocumentFormat.URL.value,
                    "job_posting_url": "https://www.wanted.co.kr/wd/366125",
                },
                files={"resume_file": ("resume.pdf", b"%PDF-1.4\n", "application/pdf")},
            )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"resume_document_id": 11, "job_posting_document_id": 22}


@pytest.mark.asyncio
async def test_parse_endpoint_rejects_resume_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/documents/parse",
            data={
                "resume_format": DocumentFormat.URL.value,
                "job_posting_format": DocumentFormat.URL.value,
                "job_posting_url": "https://www.wanted.co.kr/wd/366125",
            },
            files={"resume_file": ("resume.pdf", b"%PDF-1.4\n", "application/pdf")},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
