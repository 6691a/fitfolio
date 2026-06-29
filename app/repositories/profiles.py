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

    async def set_job_posting_embedding(self, *, document_id: int, embedding: list[float]) -> None:
        """채용공고 프로필 행에 의미 검색용 임베딩 벡터를 저장한다.

        Args:
            document_id: 임베딩을 저장할 채용공고 문서 ID.
            embedding: 저장할 임베딩 벡터(프로필이 없으면 무시).
        """
        async with self._session_factory() as session:
            record = await session.scalar(select(JobPostingProfile).where(JobPostingProfile.document_id == document_id))
            if record is None:
                return
            record.embedding = embedding
            await session.commit()

    async def list_job_postings_without_embedding(self) -> list[JobPostingProfile]:
        """임베딩이 아직 없는 채용공고 프로필을 모두 조회한다(백필용).

        Returns:
            embedding이 NULL인 JobPostingProfile 목록.
        """
        async with self._session_factory() as session:
            rows = await session.scalars(select(JobPostingProfile).where(JobPostingProfile.embedding.is_(None)))
            return list(rows.all())

    async def search_job_postings(self, *, embedding: list[float], limit: int) -> list[tuple[JobPostingProfile, float]]:
        """임베딩 코사인 거리로 가까운 채용공고 프로필을 정렬해 반환한다.

        Args:
            embedding: 검색 질의 임베딩 벡터.
            limit: 최대 결과 수.

        Returns:
            (채용공고 프로필, 코사인 거리) 튜플 목록. 거리가 작을수록 유사하다.
        """
        distance = JobPostingProfile.embedding.cosine_distance(embedding).label("distance")
        async with self._session_factory() as session:
            rows = await session.execute(
                select(JobPostingProfile, distance)
                .where(JobPostingProfile.embedding.is_not(None))
                .order_by(distance)
                .limit(limit)
            )
            return [(row[0], row[1]) for row in rows.all()]
