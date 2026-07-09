from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.config.containers import Container
from app.controllers.auth import get_current_user
from app.schemas.auth import PublicUser
from app.schemas.preferences import PreferencesOut, PreferencesUpdate
from app.services.preferences import PreferencesService

router = APIRouter(prefix="/me/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesOut)
@inject
async def get_preferences(
    current_user: PublicUser = Depends(get_current_user),
    preferences: PreferencesService = Depends(Provide[Container.preferences_service]),
):
    """현재 사용자의 개인화 프로필을 조회한다(없으면 빈 값).

    Args:
        current_user: 인증된 현재 사용자.
        preferences: 컨테이너가 주입하는 PreferencesService.

    Returns:
        개인화 프로필(저장값 + 자동 추출 제안값). 설정 전이면 저장값 필드는 None.
    """
    return await preferences.get(current_user.id)


@router.put("", response_model=PreferencesOut)
@inject
async def update_preferences(
    payload: PreferencesUpdate,
    current_user: PublicUser = Depends(get_current_user),
    preferences: PreferencesService = Depends(Provide[Container.preferences_service]),
):
    """현재 사용자의 개인화 프로필을 생성하거나 갱신한다.

    Args:
        payload: 저장할 개인화 프로필 값.
        current_user: 인증된 현재 사용자.
        preferences: 컨테이너가 주입하는 PreferencesService.

    Returns:
        저장된 개인화 프로필.
    """
    return await preferences.update(current_user.id, payload)
