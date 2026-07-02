from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.containers import Container
from app.schemas.auth import LoginRequest, PublicUser, SignupRequest, TokenResponse
from app.services.auth import AuthService
from app.services.errors import InvalidTokenError

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


def _extract_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    """HTTP Bearer 인증 정보에서 토큰 문자열을 꺼낸다.

    Args:
        credentials: FastAPI 보안 의존성이 파싱한 인증 정보.

    Returns:
        Bearer 토큰 문자열.

    Raises:
        InvalidTokenError: 인증 정보가 없거나 Bearer 방식이 아닐 때.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise InvalidTokenError("인증 토큰이 필요합니다")
    return credentials.credentials


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@inject
async def signup(
    payload: SignupRequest,
    auth: AuthService = Depends(Provide[Container.auth_service]),
) -> TokenResponse:
    """회원가입 요청을 처리한다.

    Args:
        payload: 회원가입 요청 데이터.
        auth: 컨테이너가 주입하는 AuthService.

    Returns:
        access token과 공개 사용자 정보.
    """
    return await auth.signup(payload)


@router.post("/login", response_model=TokenResponse)
@inject
async def login(
    payload: LoginRequest,
    auth: AuthService = Depends(Provide[Container.auth_service]),
) -> TokenResponse:
    """로그인 요청을 처리한다.

    Args:
        payload: 로그인 요청 데이터.
        auth: 컨테이너가 주입하는 AuthService.

    Returns:
        access token과 공개 사용자 정보.
    """
    return await auth.login(payload)


@router.get("/me", response_model=PublicUser)
@inject
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthService = Depends(Provide[Container.auth_service]),
) -> PublicUser:
    """현재 로그인한 사용자 정보를 반환한다.

    Args:
        credentials: Authorization 헤더에서 파싱된 Bearer 인증 정보.
        auth: 컨테이너가 주입하는 AuthService.

    Returns:
        공개 사용자 정보.
    """
    return await auth.get_current_user(_extract_bearer_token(credentials))


@router.get("/me", response_model=PublicUser)
async def me(user: PublicUser = Depends(get_current_user)) -> PublicUser:
    """현재 로그인한 사용자 정보를 반환한다.

    Args:
        user: Bearer 토큰으로 조회한 현재 사용자.

    Returns:
        공개 사용자 정보.
    """
    return user
