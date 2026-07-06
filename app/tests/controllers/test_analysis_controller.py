from datetime import UTC, datetime

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app, container
from app.schemas.analyses import (
    AnalysisAccepted,
    AnalysisListItem,
    AnalysisStatus,
    FitAnalysisResult,
    FitDimension,
    InterviewPreparationResult,
)
from app.schemas.auth import PublicUser
from app.schemas.documents import ParseStatus
from app.services.errors import AnalysisNotReadyError, ProfileNotReadyError


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


def _fit_result() -> FitAnalysisResult:
    return FitAnalysisResult(
        overall_score=80,
        summary="적합",
        matched_skills=["Python"],
        missing_skills=["Kubernetes"],
        skill=FitDimension(score=85, comment="기술 일치"),
        career=FitDimension(score=75, comment="경력 충족"),
        education=FitDimension(score=70, comment="정보 부족"),
        strengths=["Python 실무 경험"],
        gaps=["Kubernetes 경험 보완"],
    )


def _interview_result() -> InterviewPreparationResult:
    return InterviewPreparationResult(
        summary="기술 강점은 살리고 부족 기술은 보완한다.",
        general_questions=[
            {
                "question": "우리 회사에 지원한 이유를 설명해주세요.",
                "answer": "채용공고의 백엔드 역할과 본인의 API 개발 경험을 연결해 답변합니다.",
                "intent": "지원동기 확인",
                "source": "job_posting",
            }
        ],
        professional_questions=[
            {
                "question": "FastAPI 경험을 설명해주세요.",
                "answer": "이력서에 있는 FastAPI 경험을 중심으로 API 설계 사례를 답변합니다.",
                "intent": "기술 경험 검증",
                "source": "matched_skills",
            }
        ],
    )


@pytest.mark.asyncio
async def test_create_analysis_endpoint_delegates_to_service():
    class FakeAnalysisService:
        async def request_analysis(self, *, user_id, resume_document_id, job_posting_document_id):
            assert user_id == 1
            assert resume_document_id == 11
            assert job_posting_document_id == 22
            return AnalysisAccepted(analysis_id=3)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.analysis_service.override(FakeAnalysisService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.post(
                "/analyses",
                headers={"Authorization": "Bearer valid-token"},
                json={"resume_document_id": 11, "job_posting_document_id": 22},
            )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"analysis_id": 3}


@pytest.mark.asyncio
async def test_create_analysis_returns_409_when_profile_not_ready():
    class FakeAnalysisService:
        async def request_analysis(self, **kwargs):
            raise ProfileNotReadyError("채용공고 파싱이 완료되지 않았습니다")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.analysis_service.override(FakeAnalysisService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.post(
                "/analyses",
                headers={"Authorization": "Bearer valid-token"},
                json={"resume_document_id": 11, "job_posting_document_id": 22},
            )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "채용공고 파싱이 완료되지 않았습니다"}


@pytest.mark.asyncio
async def test_get_analysis_endpoint_returns_status_with_result():
    class FakeAnalysisService:
        async def get_analysis(self, *, analysis_id, user_id):
            assert analysis_id == 3
            assert user_id == 1
            return AnalysisStatus(analysis_id=3, status=ParseStatus.DONE, result=_fit_result())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.analysis_service.override(FakeAnalysisService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.get("/analyses/3", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "done"
    assert body["result"]["overall_score"] == 80
    assert body["result"]["matched_skills"] == ["Python"]


@pytest.mark.asyncio
async def test_list_analyses_endpoint_delegates_to_service():
    class FakeAnalysisService:
        async def list_analyses(self, *, user_id, limit):
            assert user_id == 1
            return [
                AnalysisListItem(
                    analysis_id=3,
                    status=ParseStatus.DONE,
                    overall_score=80,
                    resume_title="이력서 제목",
                    resume_name="홍길동",
                    company_name="회사",
                    job_posting_title="백엔드 개발자",
                    created_at=datetime(2026, 7, 3, tzinfo=UTC),
                )
            ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.analysis_service.override(FakeAnalysisService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.get("/analyses", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 1
    assert body[0]["analysis_id"] == 3
    assert body[0]["overall_score"] == 80
    assert body[0]["company_name"] == "회사"


@pytest.mark.asyncio
async def test_get_analysis_endpoint_returns_404_when_missing():
    class FakeAnalysisService:
        async def get_analysis(self, *, analysis_id, user_id):
            return None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.analysis_service.override(FakeAnalysisService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.get("/analyses/999", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_analysis_endpoint_returns_204():
    class FakeAnalysisService:
        async def delete_analysis(self, *, analysis_id, user_id):
            assert analysis_id == 3
            assert user_id == 1
            return True

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.analysis_service.override(FakeAnalysisService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.delete("/analyses/3", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_delete_analysis_endpoint_returns_404_when_missing():
    class FakeAnalysisService:
        async def delete_analysis(self, *, analysis_id, user_id):
            return False

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.analysis_service.override(FakeAnalysisService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.delete("/analyses/999", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_prepare_interview_endpoint_delegates_to_service():
    class FakeAnalysisService:
        async def prepare_interview(self, *, analysis_id, user_id):
            assert analysis_id == 3
            assert user_id == 1
            return _interview_result()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.analysis_service.override(FakeAnalysisService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.post(
                "/analyses/3/interview-prep",
                headers={"Authorization": "Bearer valid-token"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["summary"] == "기술 강점은 살리고 부족 기술은 보완한다."
    assert response.json()["general_questions"][0]["question"] == "우리 회사에 지원한 이유를 설명해주세요."
    assert response.json()["professional_questions"][0]["question"] == "FastAPI 경험을 설명해주세요."


@pytest.mark.asyncio
async def test_prepare_interview_endpoint_returns_409_when_analysis_not_done():
    class FakeAnalysisService:
        async def prepare_interview(self, **kwargs):
            raise AnalysisNotReadyError("완료된 분석에서만 면접 질문을 만들 수 있습니다")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.analysis_service.override(FakeAnalysisService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.post(
                "/analyses/3/interview-prep",
                headers={"Authorization": "Bearer valid-token"},
            )

    assert response.status_code == status.HTTP_409_CONFLICT
