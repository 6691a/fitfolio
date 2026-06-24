from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.schemas.documents import DocumentFormat, DocumentKind, ParseStatus

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class DocumentsRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        *,
        document_type: DocumentKind,
        format: DocumentFormat,
        file_name: str | None = None,
        file_path: str | None = None,
        content_type: str | None = None,
        source_url: str | None = None,
    ) -> Document:
        async with self._session_factory() as session:
            record = Document(
                document_type=document_type,
                format=format.value,
                file_name=file_name,
                file_path=file_path,
                content_type=content_type,
                source_url=source_url,
                status=ParseStatus.PENDING,
            )
            session.add(record)
            await session.commit()
            return record

    async def get(self, document_id: int) -> Document | None:
        async with self._session_factory() as session:
            return await session.get(Document, document_id)

    async def mark_started(self, document_id: int) -> None:
        async with self._session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                return
            document.status = ParseStatus.STARTED
            await session.commit()

    async def mark_done(self, document_id: int, *, extracted_text: str, metadata: dict) -> None:
        async with self._session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                return
            document.status = ParseStatus.DONE
            document.extracted_text = extracted_text
            document.extracted_metadata = metadata
            await session.commit()

    async def mark_failed(self, document_id: int, *, error: str) -> None:
        async with self._session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                return
            document.status = ParseStatus.FAILED
            document.error = error
            await session.commit()
