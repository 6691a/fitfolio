import logging

from app.models import UserPreferences
from app.repositories.preferences import PreferencesRepository
from app.repositories.user_profiles import UserProfilesRepository
from app.schemas.preferences import PreferencesOut, PreferencesUpdate

logger = logging.getLogger(__name__)


class PreferencesService:
    def __init__(
        self,
        preferences_repository: PreferencesRepository,
        user_profiles_repository: UserProfilesRepository,
    ) -> None:
        """개인화 프로필 조회/저장과 자동 제안값 조회에 쓸 레포지토리를 보관한다.

        Args:
            preferences_repository: 개인화 프로필 영속화 레포지토리.
            user_profiles_repository: 집계 프로필 조회 레포지토리(제안값 출처).
        """
        self._preferences = preferences_repository
        self._user_profiles = user_profiles_repository

    async def _suggested(self, user_id: int) -> tuple[str | None, str | None]:
        """물질화된 집계 프로필에서 관심 직군·기술 제안값을 읽는다(fail-soft).

        조회 실패는 개인화 프로필 조회 자체를 막지 않도록 빈 제안으로 폴백하되 원인을 로깅한다.

        Args:
            user_id: 제안값을 조회할 사용자 ID.

        Returns:
            (제안 직군 문자열, 제안 기술 문자열). 없거나 실패하면 (None, None).
        """
        try:
            profile = await self._user_profiles.get_by_user(user_id)
        except Exception as exc:
            logger.warning("관심 제안값 조회 실패, 제안 없이 진행: user_id=%s error=%s", user_id, exc)
            return None, None
        if profile is None:
            return None, None
        return (
            ", ".join(profile.interest_domains) or None,
            ", ".join(profile.interest_tech) or None,
        )

    async def get(self, user_id: int) -> PreferencesOut:
        """사용자의 저장된 개인화 프로필과 집계 기반 제안값을 함께 반환한다.

        Args:
            user_id: 프로필을 조회할 사용자 ID.

        Returns:
            저장값(없으면 None) + 집계 프로필 기반 제안값(suggested_*)을 담은 PreferencesOut.
        """
        record = await self._preferences.get_by_user(user_id)
        suggested_jobs, suggested_skills = await self._suggested(user_id)
        return PreferencesOut(
            interest_jobs=record.interest_jobs if record else None,
            interest_skills=record.interest_skills if record else None,
            notes=record.notes if record else None,
            suggested_jobs=suggested_jobs,
            suggested_skills=suggested_skills,
        )

    async def update(self, user_id: int, payload: PreferencesUpdate) -> UserPreferences:
        """사용자의 개인화 프로필을 생성하거나 갱신한다.

        Args:
            user_id: 프로필 소유자 ID.
            payload: 저장할 개인화 프로필 값.

        Returns:
            저장된 UserPreferences 레코드.
        """
        return await self._preferences.upsert(
            user_id,
            interest_jobs=payload.interest_jobs,
            interest_skills=payload.interest_skills,
            notes=payload.notes,
        )
