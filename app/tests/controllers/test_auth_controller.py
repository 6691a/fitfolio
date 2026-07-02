from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.auth import LoginRequest, PublicUser, SignupRequest, TokenResponse


@dataclass
class FakeAuthService:
    async def signup(self, payload: SignupRequest) -> TokenResponse:
        """회원가입 요청을 검증하고 고정 응답을 반환한다."""
        assert payload.email == "user@example.com"
        assert payload.password == "password123"
        assert payload.nickname == "사용자"
        return TokenResponse(
            access_token="signup-token",
            user=PublicUser(
                id=1,
                email=payload.email,
                nickname=payload.nickname,
                created_at=datetime(2026, 7, 1, tzinfo=UTC),
            ),
        )

    async def login(self, payload: LoginRequest) -> TokenResponse:
        """로그인 요청을 검증하고 고정 응답을 반환한다."""
        assert payload.email == "user@example.com"
        assert payload.password == "password123"
        return TokenResponse(
            access_token="login-token",
            user=PublicUser(
                id=1,
                email=payload.email,
                nickname="사용자",
                created_at=datetime(2026, 7, 1, tzinfo=UTC),
            ),
        )

    async def get_current_user(self, token: str) -> PublicUser:
        """Bearer 토큰을 검증하고 현재 사용자를 반환한다."""
        assert token == "valid-token"
        return PublicUser(
            id=1,
            email="user@example.com",
            nickname="사용자",
            created_at=datetime(2026, 7, 1, tzinfo=UTC),
        )


@pytest.mark.asyncio
async def test_signup_endpoint_delegates_to_auth_service():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # pyrefly: ignore [missing-attribute]
        with app.container.auth_service.override(FakeAuthService()):
            response = await client.post(
                "/auth/signup",
                json={"email": "user@example.com", "password": "password123", "nickname": "사용자"},
            )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["access_token"] == "signup-token"
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_login_endpoint_delegates_to_auth_service():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # pyrefly: ignore [missing-attribute]
        with app.container.auth_service.override(FakeAuthService()):
            response = await client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "password123"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["access_token"] == "login-token"
    assert response.json()["user"]["nickname"] == "사용자"


@pytest.mark.asyncio
async def test_me_endpoint_returns_current_user_from_bearer_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # pyrefly: ignore [missing-attribute]
        with app.container.auth_service.override(FakeAuthService()):
            response = await client.get("/auth/me", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "user@example.com"
    assert response.json()["nickname"] == "사용자"


@pytest.mark.asyncio
async def test_me_endpoint_rejects_missing_bearer_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/auth/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
