import logging

from app.repositories.analyses import AnalysesRepository
from app.repositories.profiles import ProfilesRepository
from app.schemas.analyses import (
    AnalysisAccepted,
    AnalysisListItem,
    AnalysisStatus,
    InterviewPreparationResult,
)
from app.schemas.documents import ParseStatus
from app.services.errors import AnalysisNotReadyError, ProfileNotReadyError, ResumeNotFoundError

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(
        self,
        analyses_repository: AnalysesRepository,
        profiles_repository: ProfilesRepository,
    ) -> None:
        """적합도 분석에 필요한 레포지토리를 보관한다.

        Args:
            analyses_repository: 분석 행 영속화 레포지토리.
            profiles_repository: 이력서/채용공고 프로필 조회 레포지토리.
        """
        self._analyses = analyses_repository
        self._profiles = profiles_repository

    async def request_analysis(
        self,
        *,
        user_id: int,
        resume_document_id: int,
        job_posting_document_id: int,
    ) -> AnalysisAccepted:
        """두 문서의 프로필 준비 상태와 소유권을 검증하고 비동기 분석 작업을 등록한다.

        Args:
            user_id: 분석을 요청한 사용자 ID.
            resume_document_id: 분석 대상 이력서 문서 ID.
            job_posting_document_id: 분석 대상 채용공고 문서 ID.

        Returns:
            생성된 분석 ID를 담은 AnalysisAccepted.

        Raises:
            ProfileNotReadyError: 이력서/채용공고 파싱이 아직 완료되지 않은 경우.
            ResumeNotFoundError: 이력서가 현재 사용자 소유가 아닌 경우.
        """
        resume = await self._profiles.get_resume_profile(document_id=resume_document_id)
        if resume is None:
            raise ProfileNotReadyError("이력서 파싱이 완료되지 않았습니다")
        if resume.user_id != user_id:
            raise ResumeNotFoundError("이력서를 찾을 수 없습니다")
        job_posting = await self._profiles.get_job_posting_profile(document_id=job_posting_document_id)
        if job_posting is None:
            raise ProfileNotReadyError("채용공고 파싱이 완료되지 않았습니다")

        record = await self._analyses.create(
            user_id=user_id,
            resume_document_id=resume_document_id,
            job_posting_document_id=job_posting_document_id,
        )

        # Container ↔ tasks 순환 import를 피하려고 호출 시점에 import한다(DocumentService와 동일).
        from app.tasks.analyses import task_analyze_fit

        task_analyze_fit.delay(record.id)
        return AnalysisAccepted(analysis_id=record.id)

    async def run(self, analysis_id: int) -> None:
        """분석 행을 실행 상태로 바꾸고 LLM 분석을 수행해 결과 또는 실패를 저장한다.

        Args:
            analysis_id: 실행할 분석 ID.
        """
        from app.ai.graph.analysis import run_analysis_graph

        await run_analysis_graph(self, analysis_id=analysis_id)

    async def prepare_interview(self, *, analysis_id: int, user_id: int) -> InterviewPreparationResult | None:
        """완료된 분석 결과를 기준으로 면접 질문/답변 예시를 생성하거나 캐시에서 반환한다.

        Args:
            analysis_id: 면접 준비를 요청한 분석 ID.
            user_id: 요청한 사용자 ID(소유권 검증).

        Returns:
            InterviewPreparationResult, 분석이 없거나 다른 사용자 소유면 None.

        Raises:
            AnalysisNotReadyError: 분석이 아직 완료되지 않았거나 생성에 실패한 경우.
        """
        record = await self._analyses.get(analysis_id)
        if record is None or record.user_id != user_id:
            return None
        if record.status != ParseStatus.DONE or not record.result:
            raise AnalysisNotReadyError("완료된 분석에서만 면접 질문을 만들 수 있습니다")
        if record.interview_preparation:
            return InterviewPreparationResult.model_validate(record.interview_preparation)

        from app.ai.graph.analysis import run_interview_preparation_graph

        state = await run_interview_preparation_graph(self, analysis_id=analysis_id)
        result = state.get("interview_preparation")
        if isinstance(result, InterviewPreparationResult):
            if not record.interview_preparation:
                await self._analyses.save_interview_preparation(
                    analysis_id,
                    interview_preparation=result.model_dump(mode="json"),
                )
            return result
        raise AnalysisNotReadyError(state.get("error") or "면접 질문을 만들 수 없습니다")

    async def list_analyses(self, *, user_id: int, limit: int = 50) -> list[AnalysisListItem]:
        """사용자의 적합도 분석 이력을 이력서/공고 표시 정보와 함께 최신순으로 조회한다.

        Args:
            user_id: 분석 이력을 조회할 사용자 ID.
            limit: 최대 결과 수.

        Returns:
            분석 이력 목록(완료 건은 종합 점수 포함).
        """
        rows = await self._analyses.list_by_user(user_id=user_id, limit=limit)
        return [
            AnalysisListItem(
                analysis_id=record.id,
                status=record.status,
                overall_score=(record.result or {}).get("overall_score"),
                resume_title=resume_title,
                resume_name=resume_name,
                company_name=company_name,
                job_posting_title=job_posting_title,
                created_at=record.created_at,
            )
            for record, resume_title, resume_name, company_name, job_posting_title in rows
        ]

    async def get_analysis(self, *, analysis_id: int, user_id: int) -> AnalysisStatus | None:
        """분석 진행 상태를 조회하고 완료 시 결과를 함께 반환한다.

        Args:
            analysis_id: 조회할 분석 ID.
            user_id: 요청한 사용자 ID(소유권 검증).

        Returns:
            AnalysisStatus, 분석이 없거나 다른 사용자 소유면 None.
        """
        record = await self._analyses.get(analysis_id)
        if record is None or record.user_id != user_id:
            return None
        return AnalysisStatus.model_validate(
            {
                "analysis_id": record.id,
                "status": record.status,
                # result 필드 타입(FitAnalysisResult)이 dict를 검증·변환한다.
                "result": record.result if record.status == ParseStatus.DONE else None,
                "error": record.error,
            }
        )

    async def delete_analysis(self, *, analysis_id: int, user_id: int) -> bool:
        """분석 이력을 soft delete로 삭제한다.

        Args:
            analysis_id: 삭제할 분석 ID.
            user_id: 요청한 사용자 ID(소유권 검증).

        Returns:
            삭제 성공 시 True, 분석이 없거나 다른 사용자 소유면 False.
        """
        return await self._analyses.soft_delete(analysis_id, user_id=user_id)
