from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config.containers import Container
from app.controllers.auth import get_current_user
from app.schemas.analyses import (
    AnalysisAccepted,
    AnalysisCreateRequest,
    AnalysisListItem,
    AnalysisStatus,
    InterviewPreparationResult,
)
from app.schemas.auth import PublicUser
from app.services.analysis import AnalysisService

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisAccepted, status_code=status.HTTP_202_ACCEPTED)
@inject
async def create_analysis(
    payload: AnalysisCreateRequest,
    current_user: PublicUser = Depends(get_current_user),
    analysis: AnalysisService = Depends(Provide[Container.analysis_service]),
):
    """이력서와 채용공고의 적합도 분석 작업을 등록한다.

    Args:
        payload: 분석 대상 이력서/채용공고 문서 ID.
        current_user: 인증된 현재 사용자(이력서 소유자).
        analysis: 컨테이너가 주입하는 AnalysisService.

    Returns:
        등록된 분석 ID를 담은 AnalysisAccepted.
    """
    return await analysis.request_analysis(
        user_id=current_user.id,
        resume_document_id=payload.resume_document_id,
        job_posting_document_id=payload.job_posting_document_id,
    )


@router.get("", response_model=list[AnalysisListItem])
@inject
async def list_analyses(
    limit: int = Query(50, ge=1, le=200),
    current_user: PublicUser = Depends(get_current_user),
    analysis: AnalysisService = Depends(Provide[Container.analysis_service]),
):
    """현재 사용자의 적합도 분석 이력을 최신순으로 조회한다.

    Args:
        limit: 최대 결과 수(1~200).
        current_user: 인증된 현재 사용자.
        analysis: 컨테이너가 주입하는 AnalysisService.

    Returns:
        분석 이력 목록(완료 건은 종합 점수 포함).
    """
    return await analysis.list_analyses(user_id=current_user.id, limit=limit)


@router.get("/{analysis_id}", response_model=AnalysisStatus)
@inject
async def get_analysis(
    analysis_id: int,
    current_user: PublicUser = Depends(get_current_user),
    analysis: AnalysisService = Depends(Provide[Container.analysis_service]),
):
    """적합도 분석 진행 상태를 조회하고 완료 시 결과를 함께 반환한다.

    Args:
        analysis_id: 상태를 조회할 분석 ID.
        current_user: 인증된 현재 사용자(소유권 검증).
        analysis: 컨테이너가 주입하는 AnalysisService.

    Returns:
        현재 상태(및 DONE이면 결과, FAILED면 오류)를 담은 AnalysisStatus.

    Raises:
        HTTPException: 해당 분석을 찾을 수 없을 때(404).
    """
    analysis_status = await analysis.get_analysis(analysis_id=analysis_id, user_id=current_user.id)
    if analysis_status is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "분석을 찾을 수 없습니다")
    return analysis_status


@router.post("/{analysis_id}/interview-prep", response_model=InterviewPreparationResult)
@inject
async def prepare_interview(
    analysis_id: int,
    current_user: PublicUser = Depends(get_current_user),
    analysis: AnalysisService = Depends(Provide[Container.analysis_service]),
):
    """완료된 적합도 분석을 기준으로 면접 질문과 답변 예시를 생성한다.

    Args:
        analysis_id: 면접 준비를 생성할 분석 ID.
        current_user: 인증된 현재 사용자(소유권 검증).
        analysis: 컨테이너가 주입하는 AnalysisService.

    Returns:
        면접 준비 질문/답변 결과.

    Raises:
        HTTPException: 해당 분석을 찾을 수 없을 때(404).
    """
    result = await analysis.prepare_interview(analysis_id=analysis_id, user_id=current_user.id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "분석을 찾을 수 없습니다")
    return result


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_analysis(
    analysis_id: int,
    current_user: PublicUser = Depends(get_current_user),
    analysis: AnalysisService = Depends(Provide[Container.analysis_service]),
):
    """적합도 분석 이력을 삭제한다(soft delete).

    Args:
        analysis_id: 삭제할 분석 ID.
        current_user: 인증된 현재 사용자(소유권 검증).
        analysis: 컨테이너가 주입하는 AnalysisService.

    Raises:
        HTTPException: 해당 분석을 찾을 수 없을 때(404).
    """
    deleted = await analysis.delete_analysis(analysis_id=analysis_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "분석을 찾을 수 없습니다")
