from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FitAnalysis, JobPostingProfile, ResumeProfile
from app.schemas.documents import ParseStatus

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class AnalysesRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        """적합도 분석 영속화에 사용할 세션 팩토리를 보관한다.

        Args:
            session_factory: 비동기 DB 세션을 여는 컨텍스트 매니저 팩토리.
        """
        self._session_factory = session_factory

    async def create(
        self,
        *,
        user_id: int,
        resume_document_id: int,
        job_posting_document_id: int,
    ) -> FitAnalysis:
        """pending 상태의 적합도 분석 행을 새로 생성한다.

        Args:
            user_id: 분석을 요청한 사용자 ID.
            resume_document_id: 분석 대상 이력서 문서 ID.
            job_posting_document_id: 분석 대상 채용공고 문서 ID.

        Returns:
            생성된 FitAnalysis 레코드.
        """
        async with self._session_factory() as session:
            record = FitAnalysis(
                user_id=user_id,
                resume_document_id=resume_document_id,
                job_posting_document_id=job_posting_document_id,
                status=ParseStatus.PENDING,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def list_by_user(
        self,
        *,
        user_id: int,
        limit: int = 50,
    ) -> list[tuple[FitAnalysis, str | None, str | None, str | None, str | None]]:
        """사용자의 적합도 분석 목록을 이력서/공고 표시 정보와 함께 최신순으로 조회한다.

        프로필이 그 사이 삭제됐을 수 있으므로 outer join으로 표시 정보는 NULL을 허용한다.

        Args:
            user_id: 분석 목록을 조회할 사용자 ID.
            limit: 최대 결과 수.

        Returns:
            (분석, 이력서 제목, 지원자 이름, 회사명, 공고 제목) 튜플 목록(생성일 내림차순).
        """
        stmt = (
            select(
                FitAnalysis,
                ResumeProfile.title,
                ResumeProfile.name,
                JobPostingProfile.company_name,
                JobPostingProfile.title,
            )
            .outerjoin(ResumeProfile, ResumeProfile.document_id == FitAnalysis.resume_document_id)
            .outerjoin(JobPostingProfile, JobPostingProfile.document_id == FitAnalysis.job_posting_document_id)
            .where(FitAnalysis.user_id == user_id, FitAnalysis.deleted_at.is_(None))
            .order_by(FitAnalysis.created_at.desc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            rows = await session.execute(stmt)
            return [(row[0], row[1], row[2], row[3], row[4]) for row in rows.all()]

    async def list_recent_analyzed_profiles(
        self,
        user_id: int,
        *,
        limit: int = 30,
    ) -> list[tuple[JobPostingProfile, ResumeProfile | None]]:
        """사용자가 최근 분석한 (채용공고 프로필, 이력서 프로필) 목록을 최신순으로 조회한다.

        관심 직무·기술 자동 추출(파생 개인화)의 원재료다. 이력서 프로필이 그 사이 삭제됐을 수
        있으므로 outer join으로 이력서 쪽 NULL을 허용한다.

        Args:
            user_id: 조회할 사용자 ID.
            limit: 최대 결과 수(최근 분석 window).

        Returns:
            (채용공고 프로필, 이력서 프로필 또는 None) 튜플 목록(분석 생성일 내림차순).
        """
        stmt = (
            select(JobPostingProfile, ResumeProfile)
            .select_from(FitAnalysis)
            .join(JobPostingProfile, JobPostingProfile.document_id == FitAnalysis.job_posting_document_id)
            .outerjoin(ResumeProfile, ResumeProfile.document_id == FitAnalysis.resume_document_id)
            .where(
                FitAnalysis.user_id == user_id,
                FitAnalysis.status == ParseStatus.DONE,
                FitAnalysis.deleted_at.is_(None),
            )
            .order_by(FitAnalysis.created_at.desc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            rows = await session.execute(stmt)
            return [(row[0], row[1]) for row in rows.all()]

    async def get(self, analysis_id: int) -> FitAnalysis | None:
        """분석 ID로 삭제되지 않은 적합도 분석 행을 조회한다.

        Args:
            analysis_id: 조회할 분석 ID.

        Returns:
            FitAnalysis 레코드, 없거나 삭제된 경우 None.
        """
        async with self._session_factory() as session:
            return await session.scalar(
                select(FitAnalysis).where(
                    FitAnalysis.id == analysis_id,
                    FitAnalysis.deleted_at.is_(None),
                )
            )

    async def soft_delete(self, analysis_id: int, *, user_id: int) -> bool:
        """소유자가 일치하고 아직 삭제되지 않은 분석 행에 삭제 시각을 기록한다(soft delete).

        소유권 확인·삭제를 단일 UPDATE로 처리해 DB 왕복을 줄인다.

        Args:
            analysis_id: 삭제할 분석 ID.
            user_id: 요청한 사용자 ID(소유권 조건).

        Returns:
            삭제된 행이 있으면 True, 없거나 타인 소유·이미 삭제됐으면 False.
        """
        stmt = (
            update(FitAnalysis)
            .where(
                FitAnalysis.id == analysis_id,
                FitAnalysis.user_id == user_id,
                FitAnalysis.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(UTC))
            .returning(FitAnalysis.id)
        )
        async with self._session_factory() as session:
            deleted_id = await session.scalar(stmt)
            await session.commit()
            return deleted_id is not None

    async def save_feedback(self, analysis_id: int, *, user_id: int, feedback: dict) -> bool:
        """완료된 분석에 소유자가 남긴 피드백을 저장한다(소유권 조건부 단일 UPDATE).

        Args:
            analysis_id: 피드백을 저장할 분석 ID.
            user_id: 요청한 사용자 ID(소유권 조건).
            feedback: 저장할 피드백 dict({rating, note}).

        Returns:
            저장된 행이 있으면 True, 없거나 타인 소유·미완료·삭제됐으면 False.
        """
        stmt = (
            update(FitAnalysis)
            .where(
                FitAnalysis.id == analysis_id,
                FitAnalysis.user_id == user_id,
                FitAnalysis.status == ParseStatus.DONE,
                FitAnalysis.deleted_at.is_(None),
            )
            .values(feedback=feedback)
            .returning(FitAnalysis.id)
        )
        async with self._session_factory() as session:
            saved_id = await session.scalar(stmt)
            await session.commit()
            return saved_id is not None

    async def list_recent_feedback(self, user_id: int, *, limit: int = 5) -> list[dict]:
        """사용자가 최근 남긴 피드백 목록을 최신순으로 조회한다(개인화 메모리용).

        Args:
            user_id: 피드백을 조회할 사용자 ID.
            limit: 최대 결과 수.

        Returns:
            피드백 dict 목록(생성일 내림차순). 없으면 빈 목록.
        """
        stmt = (
            select(FitAnalysis.feedback)
            .where(
                FitAnalysis.user_id == user_id,
                FitAnalysis.feedback.is_not(None),
                FitAnalysis.deleted_at.is_(None),
            )
            .order_by(FitAnalysis.created_at.desc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            rows = await session.scalars(stmt)
            return [feedback for feedback in rows.all() if feedback]

    async def mark_started(self, analysis_id: int) -> None:
        """분석 상태를 started로 바꾼다.

        Args:
            analysis_id: 상태를 바꿀 분석 ID.
        """
        await self._update(analysis_id, status=ParseStatus.STARTED)

    async def mark_done(self, analysis_id: int, *, result: dict) -> None:
        """분석 결과를 저장하고 상태를 done으로 바꾼다.

        Args:
            analysis_id: 상태를 바꿀 분석 ID.
            result: FitAnalysisResult 직렬화 JSON.
        """
        await self._update(analysis_id, status=ParseStatus.DONE, result=result, error=None)

    async def save_interview_preparation(self, analysis_id: int, *, interview_preparation: dict) -> None:
        """면접 준비 질문/답변 결과를 분석 행에 캐시한다.

        Args:
            analysis_id: 면접 준비 결과를 저장할 분석 ID.
            interview_preparation: InterviewPreparationResult 직렬화 JSON.
        """
        await self._update(analysis_id, interview_preparation=interview_preparation)

    async def mark_failed(self, analysis_id: int, *, error: str) -> None:
        """분석 상태를 failed로 바꾸고 오류 메시지를 저장한다.

        Args:
            analysis_id: 상태를 바꿀 분석 ID.
            error: 저장할 오류 메시지.
        """
        await self._update(analysis_id, status=ParseStatus.FAILED, error=error[:1000])

    async def _update(self, analysis_id: int, **values) -> None:
        """분석 행의 필드를 갱신한다(행이 없으면 무시).

        Args:
            analysis_id: 갱신할 분석 ID.
            **values: 갱신할 필드-값 쌍.
        """
        async with self._session_factory() as session:
            record = await session.scalar(
                select(FitAnalysis).where(
                    FitAnalysis.id == analysis_id,
                    FitAnalysis.deleted_at.is_(None),
                )
            )
            if record is None:
                return
            for field, value in values.items():
                setattr(record, field, value)
            await session.commit()
