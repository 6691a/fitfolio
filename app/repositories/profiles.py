from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import func, null, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobPostingProfile, ResumeProfile
from app.schemas.documents import EmploymentType, Region
from app.schemas.profiles import JobPostingProfileData, ResumeProfileData

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

# 채용공고 목록 정렬 허용 컬럼(컨트롤러 Literal과 일치).
_SORT_COLUMNS = {
    "created_at": JobPostingProfile.created_at,
    "start_date": JobPostingProfile.start_date,
    "end_date": JobPostingProfile.end_date,
}


def _ilike_pattern(value: str) -> str:
    """ILIKE 부분일치 패턴(%값%)을 만들고 와일드카드(%, _)·escape를 리터럴 처리한다."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


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

    async def set_job_posting_search_text(self, *, document_id: int, search_text: str) -> None:
        """채용공고 프로필 행에 FTS용 검색 텍스트를 저장한다.

        Args:
            document_id: 검색 텍스트를 저장할 채용공고 문서 ID.
            search_text: 저장할 합성 검색 텍스트(프로필이 없으면 무시).
        """
        async with self._session_factory() as session:
            record = await session.scalar(select(JobPostingProfile).where(JobPostingProfile.document_id == document_id))
            if record is None:
                return
            record.search_text = search_text
            await session.commit()

    async def list_job_postings_without_search_text(self) -> list[JobPostingProfile]:
        """검색 텍스트가 아직 없는 채용공고 프로필을 모두 조회한다(백필용).

        Returns:
            search_text가 NULL인 JobPostingProfile 목록.
        """
        async with self._session_factory() as session:
            rows = await session.scalars(select(JobPostingProfile).where(JobPostingProfile.search_text.is_(None)))
            return list(rows.all())

    async def list_job_postings(
        self,
        *,
        query: str | None = None,
        employment_type: EmploymentType | None = None,
        region: Region | None = None,
        sort: str = "created_at",
        order: str = "desc",
        limit: int = 50,
    ) -> list[tuple[JobPostingProfile, float | None]]:
        """채용공고 프로필을 검색어·필터·정렬 조건으로 조회한다.

        검색어가 있으면 `search_text` pg_trgm 부분일치로 거르고 word_similarity를 점수로 함께
        반환한다. employment_type/region은 enum 정확일치 필터다.

        Args:
            query: 검색어(회사명·기술스택 등). None이면 전체 목록.
            employment_type: 채용 형태 enum 필터.
            region: 근무지 대분류(시/도) enum 필터.
            sort: 정렬 기준(created_at/start_date/end_date).
            order: 정렬 방향(asc/desc).
            limit: 최대 결과 수.

        Returns:
            (채용공고 프로필, 관련도 점수 또는 None) 튜플 목록.
        """
        sort_column = _SORT_COLUMNS.get(sort, JobPostingProfile.created_at)
        ordered = (sort_column.asc() if order == "asc" else sort_column.desc()).nulls_last()
        score = func.word_similarity(query, JobPostingProfile.search_text).label("score") if query else null()

        stmt = select(JobPostingProfile, score)
        if query:
            stmt = stmt.where(JobPostingProfile.search_text.ilike(_ilike_pattern(query), escape="\\"))
        if employment_type is not None:
            stmt = stmt.where(JobPostingProfile.employment_type == employment_type)
        if region is not None:
            stmt = stmt.where(JobPostingProfile.region == region)
        stmt = stmt.order_by(ordered).limit(limit)

        async with self._session_factory() as session:
            rows = await session.execute(stmt)
            return [(row[0], row[1]) for row in rows.all()]
