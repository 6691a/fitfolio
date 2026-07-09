from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserProfile

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class UserProfilesRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        """집계 사용자 프로필 영속화에 사용할 세션 팩토리를 보관한다.

        Args:
            session_factory: 비동기 DB 세션을 여는 컨텍스트 매니저 팩토리.
        """
        self._session_factory = session_factory

    async def get_by_user(self, user_id: int) -> UserProfile | None:
        """사용자의 집계 프로필을 조회한다.

        Args:
            user_id: 프로필을 조회할 사용자 ID.

        Returns:
            UserProfile 레코드, 아직 집계되지 않았으면 None.
        """
        async with self._session_factory() as session:
            return await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))

    async def upsert(
        self,
        user_id: int,
        *,
        interest_domains: list,
        interest_tech: list,
        own_skills: list,
        experience_months: int | None,
    ) -> UserProfile:
        """사용자의 집계 프로필을 생성하거나 갱신한다(사용자당 1행, 멱등 재빌드).

        Args:
            user_id: 프로필 소유자 ID.
            interest_domains: 관심 직군 태그(최근성 가중 상위).
            interest_tech: 관심 기술 태그(최근성 가중 상위).
            own_skills: 사용자 보유 기술.
            experience_months: 총 경력 개월 수(없으면 None).

        Returns:
            생성 또는 갱신된 UserProfile 레코드.
        """
        values = {
            "interest_domains": interest_domains,
            "interest_tech": interest_tech,
            "own_skills": own_skills,
            "experience_months": experience_months,
        }
        async with self._session_factory() as session:
            record = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
            if record is None:
                record = UserProfile(user_id=user_id, **values)
                session.add(record)
            else:
                for field, value in values.items():
                    setattr(record, field, value)
            await session.commit()
            await session.refresh(record)
            return record
