from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.schemas.auth import LoginRequest, SignupRequest
from app.security.auth import verify_password
from app.services.auth import AuthService
from app.services.errors import AuthConflictError, InvalidCredentialsError, InvalidTokenError


@dataclass
class FakeSettings:
    AUTH_SECRET_KEY: str = "test-secret-for-auth-that-is-long-enough"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    AUTH_ALGORITHM: str = "HS256"


@dataclass
class FakeUser:
    id: int
    email: str
    hashed_password: str
    nickname: str
    created_at: datetime


class FakeUsersRepository:
    def __init__(self) -> None:
        self.users: list[FakeUser] = []

    async def create(self, *, email: str, hashed_password: str, nickname: str) -> FakeUser:
        """테스트용 사용자 레코드를 생성한다."""
        user = FakeUser(
            id=len(self.users) + 1,
            email=email,
            hashed_password=hashed_password,
            nickname=nickname,
            created_at=datetime(2026, 7, 1, tzinfo=UTC),
        )
        self.users.append(user)
        return user

    async def get(self, user_id: int) -> FakeUser | None:
        """ID로 테스트용 사용자를 조회한다."""
        return next((user for user in self.users if user.id == user_id), None)

    async def get_by_email(self, email: str) -> FakeUser | None:
        """이메일로 테스트용 사용자를 조회한다."""
        return next((user for user in self.users if user.email == email), None)

    async def get_by_nickname(self, nickname: str) -> FakeUser | None:
        """닉네임으로 테스트용 사용자를 조회한다."""
        return next((user for user in self.users if user.nickname == nickname), None)


@pytest.fixture
def users_repository() -> FakeUsersRepository:
    return FakeUsersRepository()


@pytest.fixture
def auth_service(users_repository: FakeUsersRepository) -> AuthService:
    return AuthService(users_repository=users_repository, settings=FakeSettings())


@pytest.mark.asyncio
async def test_signup_hashes_password_and_returns_public_token_response(
    auth_service: AuthService,
    users_repository: FakeUsersRepository,
):
    response = await auth_service.signup(
        SignupRequest(email="user@example.com", password="password123", nickname="사용자")
    )

    stored = users_repository.users[0]
    assert stored.hashed_password != "password123"
    assert verify_password("password123", stored.hashed_password)
    assert response.access_token
    assert response.token_type == "bearer"
    assert response.user.email == "user@example.com"
    assert response.user.nickname == "사용자"
    assert not hasattr(response.user, "password")
    assert not hasattr(response.user, "hashed_password")


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_email(auth_service: AuthService):
    await auth_service.signup(SignupRequest(email="user@example.com", password="password123", nickname="사용자"))

    with pytest.raises(AuthConflictError, match="이미 사용 중인 이메일입니다"):
        await auth_service.signup(
            SignupRequest(email="user@example.com", password="password123", nickname="다른사용자")
        )


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_nickname(auth_service: AuthService):
    await auth_service.signup(SignupRequest(email="user@example.com", password="password123", nickname="사용자"))

    with pytest.raises(AuthConflictError, match="이미 사용 중인 닉네임입니다"):
        await auth_service.signup(SignupRequest(email="other@example.com", password="password123", nickname="사용자"))


@pytest.mark.asyncio
async def test_login_returns_token_for_valid_credentials(auth_service: AuthService):
    await auth_service.signup(SignupRequest(email="user@example.com", password="password123", nickname="사용자"))

    response = await auth_service.login(LoginRequest(email="user@example.com", password="password123"))

    assert response.access_token
    assert response.user.email == "user@example.com"


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(auth_service: AuthService):
    await auth_service.signup(SignupRequest(email="user@example.com", password="password123", nickname="사용자"))

    with pytest.raises(InvalidCredentialsError, match="이메일 또는 비밀번호가 올바르지 않습니다"):
        await auth_service.login(LoginRequest(email="user@example.com", password="wrong-password"))


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(auth_service: AuthService):
    with pytest.raises(InvalidCredentialsError, match="이메일 또는 비밀번호가 올바르지 않습니다"):
        await auth_service.login(LoginRequest(email="missing@example.com", password="password123"))


@pytest.mark.asyncio
async def test_get_current_user_returns_token_subject(auth_service: AuthService):
    signup = await auth_service.signup(
        SignupRequest(email="user@example.com", password="password123", nickname="사용자")
    )

    user = await auth_service.get_current_user(signup.access_token)

    assert user.email == "user@example.com"
    assert user.nickname == "사용자"


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token(auth_service: AuthService):
    with pytest.raises(InvalidTokenError, match="인증 토큰이 올바르지 않습니다"):
        await auth_service.get_current_user("not-a-token")
