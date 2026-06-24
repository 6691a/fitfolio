import asyncio

from dependency_injector.wiring import Provide, inject

from app.celery_app import celery_app
from app.config.containers import Container
from app.database.session import Database
from app.repositories.documents import DocumentsRepository
from app.repositories.profiles import ProfilesRepository
from app.schemas.documents import DocumentFormat, DocumentInput, DocumentKind, FileInput, ParsedDocument, UrlInput
from app.schemas.profiles import JobPostingProfileData, ResumeProfileData
from app.services.document import DocumentService
from app.services.profiles import build_profile_data


def _build_document_input(document) -> DocumentInput:
    document_format = DocumentFormat(document.format)
    match document_format:
        case DocumentFormat.URL:
            return UrlInput(
                document_type=document.document_type,
                input_type=DocumentFormat.URL,
                url=document.source_url,
            )
        case DocumentFormat.PDF | DocumentFormat.DOCX | DocumentFormat.IMAGE | DocumentFormat.PPT:
            return FileInput(
                document_type=document.document_type,
                input_type=document_format,
                file_path=document.file_path,
                file_name=document.file_name,
                content_type=document.content_type,
            )

    raise ValueError(f"Unsupported document format: {document_format}")


async def _store_profile(profiles_repository: ProfilesRepository, document, parsed: ParsedDocument) -> None:
    profile = build_profile_data(DocumentKind(document.document_type), parsed)
    if isinstance(profile, ResumeProfileData):
        await profiles_repository.upsert_resume_profile(document_id=document.id, profile=profile)
        return

    if isinstance(profile, JobPostingProfileData):
        await profiles_repository.upsert_job_posting_profile(document_id=document.id, profile=profile)


@celery_app.task(name="documents.parse")
def task_parse_document(document_id: int) -> None:
    asyncio.run(_parse_document(document_id))


@inject
async def _parse_document(
    document_id: int,
    database: Database = Provide[Container.worker_database],
) -> None:
    try:
        documents_repository = DocumentsRepository(session_factory=database.async_session)
        profiles_repository = ProfilesRepository(session_factory=database.async_session)
        document_service = DocumentService(documents_repository=documents_repository)

        document = await documents_repository.get(document_id)
        if document is None:
            return

        await documents_repository.mark_started(document_id)

        document_input = _build_document_input(document)

        try:
            parsed = await document_service.parse(document_input)
        except Exception as exc:
            await documents_repository.mark_failed(document_id, error=str(exc))
        else:
            await documents_repository.mark_done(
                document_id,
                extracted_text=parsed.extracted_text,
                metadata=parsed.metadata,
            )
            await _store_profile(profiles_repository, document, parsed)
    finally:
        await database.dispose()
