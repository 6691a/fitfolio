from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobPostingProfile, ResumeProfile
from app.schemas.profiles import JobPostingProfileData, ResumeProfileData

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class ProfilesRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        """프로필 영속화에 사용할 세션 팩토리를 보관한다.

        Args:
            session_factory: 비동기 DB 세션을 여는 컨텍스트 매니저 팩토리.
        """
        self._session_factory = session_factory

    async def upsert_resume_profile(self, *, document_id: int, profile: ResumeProfileData) -> ResumeProfile:
        """이력서 프로필을 문서 ID 기준으로 생성하거나 갱신한다.

        Args:
            document_id: 프로필이 속한 문서의 ID.
            profile: 저장할 이력서 프로필 데이터.

        Returns:
            생성 또는 갱신된 ResumeProfile 레코드.
        """
        values = profile.model_dump()
        async with self._session_factory() as session:
            record = await session.scalar(select(ResumeProfile).where(ResumeProfile.document_id == document_id))
            if record is None:
                record = ResumeProfile(document_id=document_id, **values)
                session.add(record)
            else:
                for field, value in values.items():
                    setattr(record, field, value)
            await session.commit()
            return record

    async def upsert_job_posting_profile(
        self,
        *,
        document_id: int,
        profile: JobPostingProfileData,
    ) -> JobPostingProfile:
        """채용공고 프로필을 문서 ID 기준으로 생성하거나 갱신한다.

        Args:
            document_id: 프로필이 속한 문서의 ID.
            profile: 저장할 채용공고 프로필 데이터.

        Returns:
            생성 또는 갱신된 JobPostingProfile 레코드.
        """
        values = profile.model_dump()
        async with self._session_factory() as session:
            record = await session.scalar(select(JobPostingProfile).where(JobPostingProfile.document_id == document_id))
            if record is None:
                record = JobPostingProfile(document_id=document_id, **values)
                session.add(record)
            else:
                for field, value in values.items():
                    setattr(record, field, value)
            await session.commit()
            return record
