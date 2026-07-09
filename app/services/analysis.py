import logging

from app.ai.interests import aggregate_user_profile
from app.repositories.analyses import AnalysesRepository
from app.repositories.preferences import PreferencesRepository
from app.repositories.profiles import ProfilesRepository
from app.repositories.user_profiles import UserProfilesRepository
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
        preferences_repository: PreferencesRepository,
        user_profiles_repository: UserProfilesRepository,
    ) -> None:
        """적합도 분석에 필요한 레포지토리를 보관한다.

        Args:
            analyses_repository: 분석 행 영속화 레포지토리.
            profiles_repository: 이력서/채용공고 프로필 조회 레포지토리.
            preferences_repository: 개인화 프로필 조회 레포지토리(답변 개인화용).
            user_profiles_repository: 집계 사용자 프로필 upsert/조회 레포지토리.
        """
        self._analyses = analyses_repository
        self._profiles = profiles_repository
        self._preferences = preferences_repository
        self._user_profiles = user_profiles_repository

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

        분석이 완료되면 사용자 집계 프로필(UserProfile)을 최근 이력에서 재빌드해 upsert한다.

        Args:
            analysis_id: 실행할 분석 ID.
        """
        from app.ai.graph.analysis import run_analysis_graph

        state = await run_analysis_graph(self, analysis_id=analysis_id)
        record = state.get("record")
        if state.get("completed") and record is not None:
            await self.refresh_user_profile(record.user_id)

    async def refresh_user_profile(self, user_id: int) -> None:
        """최근 분석 이력 전체에서 사용자 집계 프로필을 재계산해 upsert한다(멱등, fail-soft).

        원본 분석에서 통째로 재계산하므로 물질화 뷰 재빌드 경로로도 그대로 쓴다. 개인화는 부가
        기능이라 실패해도 분석 완료는 유지하되, 원인은 반드시 로깅한다.

        Args:
            user_id: 집계 프로필을 갱신할 사용자 ID.
        """
        try:
            recent = await self._analyses.list_recent_analyzed_profiles(user_id)
            data = aggregate_user_profile(recent)
            await self._user_profiles.upsert(
                user_id,
                interest_domains=data.interest_domains,
                interest_tech=data.interest_tech,
                own_skills=data.own_skills,
                experience_months=data.experience_months,
            )
        except Exception as exc:
            logger.warning("사용자 집계 프로필 갱신 실패, 분석 완료는 유지: user_id=%s error=%s", user_id, exc)

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

    async def submit_feedback(self, *, analysis_id: int, user_id: int, rating: float, note: str) -> bool:
        """완료된 분석에 사용자의 별점·메모 피드백을 저장한다(다음 답변 개인화에 쓰인다).

        Args:
            analysis_id: 피드백을 남길 분석 ID.
            user_id: 요청한 사용자 ID(소유권 검증).
            rating: 별점(0.5~5.0).
            note: 자유 피드백 메모.

        Returns:
            저장 성공 시 True, 분석이 없거나 다른 사용자 소유면 False.

        Raises:
            AnalysisNotReadyError: 분석이 아직 완료되지 않은 경우.
        """
        record = await self._analyses.get(analysis_id)
        if record is None or record.user_id != user_id:
            return False
        if record.status != ParseStatus.DONE:
            raise AnalysisNotReadyError("완료된 분석에만 피드백을 남길 수 있습니다")
        return await self._analyses.save_feedback(
            analysis_id,
            user_id=user_id,
            feedback={"rating": rating, "note": note},
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
