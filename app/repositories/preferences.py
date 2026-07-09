from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserPreferences

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class PreferencesRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        """개인화 프로필 영속화에 사용할 세션 팩토리를 보관한다.

        Args:
            session_factory: 비동기 DB 세션을 여는 컨텍스트 매니저 팩토리.
        """
        self._session_factory = session_factory

    async def get_by_user(self, user_id: int) -> UserPreferences | None:
        """사용자의 개인화 프로필을 조회한다.

        Args:
            user_id: 프로필을 조회할 사용자 ID.

        Returns:
            UserPreferences 레코드, 아직 설정하지 않았으면 None.
        """
        async with self._session_factory() as session:
            return await session.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))

    async def upsert(
        self,
        user_id: int,
        *,
        interest_jobs: str | None,
        interest_skills: str | None,
        notes: str | None,
    ) -> UserPreferences:
        """사용자의 개인화 프로필을 생성하거나 갱신한다(사용자당 1행).

        Args:
            user_id: 프로필 소유자 ID.
            interest_jobs: 관심 직무(사용자 수정본).
            interest_skills: 관심 기술/역량(사용자 수정본).
            notes: 자유 기타 메모.

        Returns:
            생성 또는 갱신된 UserPreferences 레코드.
        """
        async with self._session_factory() as session:
            record = await session.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
            if record is None:
                record = UserPreferences(
                    user_id=user_id,
                    interest_jobs=interest_jobs,
                    interest_skills=interest_skills,
                    notes=notes,
                )
                session.add(record)
            else:
                record.interest_jobs = interest_jobs
                record.interest_skills = interest_skills
                record.notes = notes
            await session.commit()
            await session.refresh(record)
            return record
