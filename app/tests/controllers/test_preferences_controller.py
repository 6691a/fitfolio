from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app, container
from app.schemas.auth import PublicUser
from app.schemas.preferences import PreferencesOut


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
async def test_get_preferences_returns_stored_and_suggested():
    class FakePreferencesService:
        async def get(self, user_id):
            assert user_id == 1
            # 저장값은 없고 최근 분석에서 자동 추출한 제안값만 있는 상태.
            return PreferencesOut(suggested_jobs="백엔드 개발자", suggested_skills="Python, AWS")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.preferences_service.override(FakePreferencesService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.get(
                "/me/preferences",
                headers={"Authorization": "Bearer valid-token"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "interest_jobs": None,
        "interest_skills": None,
        "notes": None,
        "suggested_jobs": "백엔드 개발자",
        "suggested_skills": "Python, AWS",
    }


@pytest.mark.asyncio
async def test_update_preferences_delegates_and_returns_saved():
    class FakePreferencesService:
        async def update(self, user_id, payload):
            assert user_id == 1
            assert payload.interest_jobs == "백엔드 개발자"
            return SimpleNamespace(
                interest_jobs=payload.interest_jobs,
                interest_skills=payload.interest_skills,
                notes=payload.notes,
            )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            container.preferences_service.override(FakePreferencesService()),
            container.auth_service.override(FakeAuthService()),
        ):
            response = await client.put(
                "/me/preferences",
                headers={"Authorization": "Bearer valid-token"},
                json={"interest_jobs": "백엔드 개발자", "interest_skills": "Python", "notes": None},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["interest_jobs"] == "백엔드 개발자"
    assert response.json()["interest_skills"] == "Python"
