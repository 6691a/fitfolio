from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import jwt
from jwt import InvalidTokenError as JwtInvalidTokenError

from app.schemas.auth import LoginRequest, PublicUser, SignupRequest, TokenResponse
from app.security.auth import hash_password, verify_password
from app.services.errors import AuthConflictError, InvalidCredentialsError, InvalidTokenError


class AuthSettings(Protocol):
    AUTH_SECRET_KEY: str
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int
    AUTH_ALGORITHM: str


class UsersRepositoryProtocol(Protocol):
    async def create(self, *, email: str, hashed_password: str, nickname: str) -> Any:
        """새 사용자를 생성한다."""

    async def get(self, user_id: int) -> Any | None:
        """ID로 사용자를 조회한다."""

    async def get_by_email(self, email: str) -> Any | None:
        """이메일로 사용자를 조회한다."""

    async def get_by_nickname(self, nickname: str) -> Any | None:
        """닉네임으로 사용자를 조회한다."""


class AuthService:
    def __init__(self, users_repository: UsersRepositoryProtocol, settings: AuthSettings) -> None:
        """인증 서비스 의존성을 보관한다.

        Args:
            users_repository: 사용자 영속화 레포지토리.
            settings: 인증 토큰 설정이 포함된 앱 설정.
        """
        self._users_repository = users_repository
        self._settings = settings

    async def signup(self, payload: SignupRequest) -> TokenResponse:
        """사용자를 생성하고 access token을 발급한다.

        Args:
            payload: 회원가입 요청 데이터.

        Returns:
            access token과 공개 사용자 정보.

        Raises:
            AuthConflictError: 이메일이나 닉네임이 이미 사용 중일 때.
        """
        if await self._users_repository.get_by_email(payload.email) is not None:
            raise AuthConflictError("이미 사용 중인 이메일입니다")
        if await self._users_repository.get_by_nickname(payload.nickname) is not None:
            raise AuthConflictError("이미 사용 중인 닉네임입니다")

        user = await self._users_repository.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            nickname=payload.nickname,
        )
        return self._token_response(PublicUser.model_validate(user))

    async def login(self, payload: LoginRequest) -> TokenResponse:
        """이메일과 비밀번호를 검증하고 access token을 발급한다.

        Args:
            payload: 로그인 요청 데이터.

        Returns:
            access token과 공개 사용자 정보.

        Raises:
            InvalidCredentialsError: 사용자가 없거나 비밀번호가 틀렸을 때.
        """
        user = await self._users_repository.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsError("이메일 또는 비밀번호가 올바르지 않습니다")
        return self._token_response(PublicUser.model_validate(user))

    async def get_current_user(self, token: str) -> PublicUser:
        """JWT access token에서 현재 사용자를 조회한다.

        Args:
            token: Bearer 토큰 문자열.

        Returns:
            공개 사용자 정보.

        Raises:
            InvalidTokenError: 토큰이 잘못됐거나 사용자를 찾을 수 없을 때.
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.AUTH_SECRET_KEY,
                algorithms=[self._settings.AUTH_ALGORITHM],
            )
            subject = payload.get("sub")
            if subject is None:
                raise InvalidTokenError("인증 토큰이 올바르지 않습니다")
            user_id = int(subject)
        except (JwtInvalidTokenError, TypeError, ValueError):
            raise InvalidTokenError("인증 토큰이 올바르지 않습니다") from None

        user = await self._users_repository.get(user_id)
        if user is None:
            raise InvalidTokenError("인증 토큰이 올바르지 않습니다")
        return PublicUser.model_validate(user)

    def create_access_token(self, user_id: int) -> str:
        """사용자 ID를 subject로 담은 access token을 만든다.

        Args:
            user_id: 토큰 subject로 사용할 사용자 ID.

        Returns:
            JWT access token 문자열.
        """
        expires_at = datetime.now(UTC) + timedelta(minutes=self._settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
        return jwt.encode(
            {"sub": str(user_id), "exp": expires_at},
            self._settings.AUTH_SECRET_KEY,
            algorithm=self._settings.AUTH_ALGORITHM,
        )

    def _token_response(self, user: PublicUser) -> TokenResponse:
        """공개 사용자 정보로 token response를 구성한다."""
        return TokenResponse(access_token=self.create_access_token(user.id), user=user)
