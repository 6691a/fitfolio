import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from datetime import UTC, datetime

from app.main import app, container
from app.schemas.auth import PublicUser
from app.schemas.documents import DocumentFormat, ParseApplicationAccepted, ParseJobAccepted
from app.schemas.profiles import ResumeListItem


class FakeAuthService:
    async def get_current_user(self, token: str) -> PublicUser:
        """테스트용 Bearer 토큰을 검증하고 사용자를 반환한다."""
        assert token == "valid-token"
        return PublicUser(
            id=1,
            email="user@example.com",
            nickname="사용자",
            created_at=datetime(2026, 7, 1, tzinfo=UTC),
        )


@pytest.mark.asyncio
async def test_parse_endpoint_delegates_to_service():
    class FakeDocumentService:
        async def request_application_parse(self, **kwargs):
            assert kwargs["resume_format"] == DocumentFormat.PDF
            assert kwargs["job_posting_format"] == DocumentFormat.URL
            return ParseApplicationAccepted(resume_document_id=11, job_posting_document_id=22)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.document_service.override(FakeDocumentService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.post(
                "/documents/parse",
                headers={"Authorization": "Bearer valid-token"},
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
async def test_upload_resume_endpoint_delegates_to_service():
    class FakeDocumentService:
        async def request_resume_parse(self, *, user_id, resume_format, resume_file):
            assert user_id == 1
            assert resume_format == DocumentFormat.PDF
            return ParseJobAccepted(document_id=5)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.document_service.override(FakeDocumentService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.post(
                "/documents/resumes",
                headers={"Authorization": "Bearer valid-token"},
                data={"resume_format": DocumentFormat.PDF.value},
                files={"resume_file": ("resume.pdf", b"%PDF-1.4\n", "application/pdf")},
            )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"document_id": 5}


@pytest.mark.asyncio
async def test_upload_job_posting_endpoint_delegates_to_service():
    class FakeDocumentService:
        async def request_job_posting_parse(self, *, user_id, job_posting_format, **kwargs):
            assert user_id == 1
            assert job_posting_format == DocumentFormat.URL
            assert kwargs["job_posting_url"] == "https://www.wanted.co.kr/wd/366125"
            return ParseJobAccepted(document_id=9)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.document_service.override(FakeDocumentService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.post(
                "/documents/job-postings",
                headers={"Authorization": "Bearer valid-token"},
                data={
                    "job_posting_format": DocumentFormat.URL.value,
                    "job_posting_url": "https://www.wanted.co.kr/wd/366125",
                },
            )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"document_id": 9}


@pytest.mark.asyncio
async def test_list_resumes_endpoint_delegates_to_service():
    class FakeDocumentService:
        async def list_resumes(self, *, user_id, limit):
            assert user_id == 1
            return [
                ResumeListItem(
                    document_id=7,
                    name="홍길동",
                    email="hong@example.com",
                    career_summary="백엔드 5년",
                    created_at=datetime(2026, 7, 1, tzinfo=UTC),
                )
            ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.document_service.override(FakeDocumentService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.get(
                "/documents/resumes",
                headers={"Authorization": "Bearer valid-token"},
            )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 1
    assert body[0]["document_id"] == 7
    assert body[0]["name"] == "홍길동"


@pytest.mark.asyncio
async def test_get_parse_status_passes_current_user_and_returns_404_when_hidden():
    class FakeDocumentService:
        async def get_parse_status(self, document_id, *, user_id):
            assert document_id == 99
            assert user_id == 1
            return None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.document_service.override(FakeDocumentService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.get(
                "/documents/parse/99",
                headers={"Authorization": "Bearer valid-token"},
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_parse_endpoint_rejects_resume_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with container.auth_service.override(FakeAuthService()):
            response = await client.post(
                "/documents/parse",
                headers={"Authorization": "Bearer valid-token"},
                data={
                    "resume_format": DocumentFormat.URL.value,
                    "job_posting_format": DocumentFormat.URL.value,
                    "job_posting_url": "https://www.wanted.co.kr/wd/366125",
                },
                files={"resume_file": ("resume.pdf", b"%PDF-1.4\n", "application/pdf")},
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_parse_endpoint_rejects_missing_auth_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/documents/parse",
            data={
                "resume_format": DocumentFormat.PDF.value,
                "job_posting_format": DocumentFormat.URL.value,
                "job_posting_url": "https://www.wanted.co.kr/wd/366125",
            },
            files={"resume_file": ("resume.pdf", b"%PDF-1.4\n", "application/pdf")},
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
