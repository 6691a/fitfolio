from typing import Literal

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.config.containers import Container
from app.schemas.documents import (
    DocumentFormat,
    EmploymentType,
    ParseApplicationAccepted,
    ParseJobStatus,
    Region,
)
from app.schemas.profiles import JobPostingListItem
from app.security.job_domains import is_allowed_job_domain
from app.services.document import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/parse", response_model=ParseApplicationAccepted, status_code=status.HTTP_202_ACCEPTED)
@inject
async def parse_document(
    resume_format: DocumentFormat = Form(...),
    job_posting_format: DocumentFormat = Form(...),
    resume_file: UploadFile = File(...),
    job_posting_file: UploadFile | None = File(None),
    job_posting_url: str | None = Form(None),
    job_posting_text: str | None = Form(None),
    document: DocumentService = Depends(Provide[Container.document_service]),
):
    """이력서와 채용공고를 검증·저장하고 비동기 파싱 작업을 등록한다.

    Args:
        resume_format: 이력서 입력 형식.
        job_posting_format: 채용공고 입력 형식.
        resume_file: 업로드된 이력서 파일.
        job_posting_file: 업로드된 채용공고 파일(URL/텍스트가 아닐 때).
        job_posting_url: 채용공고 URL(URL 입력일 때).
        job_posting_text: 채용공고 본문(텍스트 입력일 때).
        document: 컨테이너가 주입하는 DocumentService.

    Returns:
        등록된 이력서/채용공고 문서 ID를 담은 ParseApplicationAccepted.

    Raises:
        HTTPException: 입력 형식·파일 정보가 올바르지 않거나(422), 지원하지 않는
            도메인(400)일 때.
    """
    if resume_format == DocumentFormat.URL:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "이력서는 URL 입력을 지원하지 않습니다")
    if resume_file.filename is None or resume_file.content_type is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "이력서 파일 정보가 올바르지 않습니다")

    if job_posting_format == DocumentFormat.URL:
        if not job_posting_url:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "채용 공고 URL이 필요합니다")
        if not is_allowed_job_domain(job_posting_url):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "지원하지 않는 도메인입니다")
    elif job_posting_format == DocumentFormat.TEXT:
        if not job_posting_text or not job_posting_text.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "채용 공고 본문이 필요합니다")
    elif job_posting_file is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "채용 공고 파일이 필요합니다")
    elif job_posting_file.filename is None or job_posting_file.content_type is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "채용 공고 파일 정보가 올바르지 않습니다")

    return await document.request_application_parse(
        resume_format=resume_format,
        resume_file=resume_file,
        job_posting_format=job_posting_format,
        job_posting_file=job_posting_file,
        job_posting_url=job_posting_url,
        job_posting_text=job_posting_text,
    )


@router.get("/job-postings", response_model=list[JobPostingListItem])
@inject
async def list_job_postings(
    q: str | None = Query(None, description="검색어(회사명·기술스택 등). 없으면 전체 목록"),
    employment_type: EmploymentType | None = Query(None, description="채용 형태 enum 필터"),
    region: Region | None = Query(None, description="근무지 대분류(시/도) enum 필터"),
    sort: Literal["created_at", "start_date", "end_date"] = Query("created_at"),
    order: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    document: DocumentService = Depends(Provide[Container.document_service]),
):
    """업로드된 채용공고를 검색어·필터·정렬로 조회한다.

    Args:
        q: 검색어(없으면 전체 목록).
        employment_type: 채용 형태 enum 필터.
        region: 근무지 대분류(시/도) enum 필터.
        sort: 정렬 기준(등록일/시작일/종료일).
        order: 정렬 방향.
        limit: 최대 결과 수(1~200).
        document: 컨테이너가 주입하는 DocumentService.

    Returns:
        조건에 맞는 채용공고 목록.
    """
    return await document.list_job_postings(
        query=q,
        employment_type=employment_type,
        region=region,
        sort=sort,
        order=order,
        limit=limit,
    )


@router.get("/parse/{document_id}", response_model=ParseJobStatus)
@inject
async def get_parse_status(
    document_id: int,
    document: DocumentService = Depends(Provide[Container.document_service]),
):
    """문서 파싱 진행 상태를 조회하고 완료 시 결과를 함께 반환한다.

    Args:
        document_id: 상태를 조회할 문서 ID.
        document: 컨테이너가 주입하는 DocumentService.

    Returns:
        현재 상태(및 DONE이면 결과, FAILED면 오류)를 담은 ParseJobStatus.

    Raises:
        HTTPException: 해당 문서를 찾을 수 없을 때(404).
    """
    job_status = await document.get_parse_status(document_id)
    if job_status is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "문서를 찾을 수 없습니다")
    return job_status
