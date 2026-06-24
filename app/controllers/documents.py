from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config.containers import Container
from app.config.settings import settings
from app.repositories.documents import DocumentsRepository
from app.schemas.documents import (
    DocumentFormat,
    DocumentKind,
    FileInput,
    ParseApplicationAccepted,
    ParsedDocument,
    ParseJobStatus,
    ParseStatus,
    UrlInput,
)
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
    document: DocumentService = Depends(Provide[Container.document_service]),
):
    if resume_format == DocumentFormat.URL:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "이력서는 URL 입력을 지원하지 않습니다")
    if resume_file.filename is None or resume_file.content_type is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "이력서 파일 정보가 올바르지 않습니다")

    if job_posting_format == DocumentFormat.URL:
        if not job_posting_url:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "채용 공고 URL이 필요합니다")
        if not is_allowed_job_domain(job_posting_url):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "지원하지 않는 도메인입니다")
    elif job_posting_file is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "채용 공고 파일이 필요합니다")
    elif job_posting_file.filename is None or job_posting_file.content_type is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "채용 공고 파일 정보가 올바르지 않습니다")

    resume_path = await document.save(
        resume_format,
        resume_file,
        document_type=DocumentKind.RESUME,
        suffix=f".{resume_format.value}",
        max_bytes=settings.MAX_PDF_BYTES,
    )
    resume_document_id = await document.request_parse(
        document_type=DocumentKind.RESUME,
        format=resume_format,
        file_name=resume_file.filename,
        file_path=str(resume_path),
        content_type=resume_file.content_type,
    )

    if job_posting_format == DocumentFormat.URL:
        assert job_posting_url is not None
        job_posting_document_id = await document.request_parse_url(
            document_type=DocumentKind.JOB_POSTING,
            url=job_posting_url,
        )
    else:
        assert job_posting_file is not None
        assert job_posting_file.filename is not None
        assert job_posting_file.content_type is not None
        job_posting_path = await document.save(
            job_posting_format,
            job_posting_file,
            document_type=DocumentKind.JOB_POSTING,
            suffix=f".{job_posting_format.value}",
            max_bytes=settings.MAX_PDF_BYTES,
        )
        job_posting_document_id = await document.request_parse(
            document_type=DocumentKind.JOB_POSTING,
            format=job_posting_format,
            file_name=job_posting_file.filename,
            file_path=str(job_posting_path),
            content_type=job_posting_file.content_type,
        )

    return ParseApplicationAccepted(
        resume_document_id=resume_document_id,
        job_posting_document_id=job_posting_document_id,
    )


@router.get("/parse/{document_id}", response_model=ParseJobStatus)
@inject
async def get_parse_status(
    document_id: int,
    documents_repository: DocumentsRepository = Depends(Provide[Container.documents_repository]),
):
    record = await documents_repository.get(document_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "문서를 찾을 수 없습니다")

    if record.status == ParseStatus.DONE:
        document_format = DocumentFormat(record.format)
        match document_format:
            case DocumentFormat.URL:
                original_input = UrlInput(
                    document_type=record.document_type,
                    input_type=DocumentFormat.URL,
                    url=record.source_url,
                )
            case DocumentFormat.PDF | DocumentFormat.DOCX | DocumentFormat.IMAGE | DocumentFormat.PPT:
                assert record.file_path is not None
                assert record.file_name is not None
                assert record.content_type is not None
                original_input = FileInput(
                    document_type=record.document_type,
                    input_type=document_format,
                    file_path=record.file_path,
                    file_name=record.file_name,
                    content_type=record.content_type,
                )
            case _:
                raise ValueError(f"Unsupported document format: {document_format}")

        result = ParsedDocument(
            original_input=original_input,
            extracted_text=record.extracted_text or "",
            metadata=record.extracted_metadata or {},
        )
        return ParseJobStatus(document_id=document_id, status=ParseStatus.DONE, result=result)

    if record.status == ParseStatus.FAILED:
        return ParseJobStatus(document_id=document_id, status=ParseStatus.FAILED, error=record.error)

    return ParseJobStatus(document_id=document_id, status=record.status)
