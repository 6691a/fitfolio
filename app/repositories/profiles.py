from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobPostingProfile, ResumeProfile
from app.schemas.profiles import JobPostingProfileData, ResumeProfileData

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class ProfilesRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def upsert_resume_profile(self, *, document_id: int, profile: ResumeProfileData) -> ResumeProfile:
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
