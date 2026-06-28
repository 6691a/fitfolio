from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.schemas.documents import DocumentFormat, DocumentKind, ParseStatus

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class DocumentsRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        """문서 영속화에 사용할 세션 팩토리를 보관한다.

        Args:
            session_factory: 비동기 DB 세션을 여는 컨텍스트 매니저 팩토리.
        """
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
        extracted_text: str | None = None,
    ) -> Document:
        """새 문서 레코드를 PENDING 상태로 생성한다.

        Args:
            document_type: 문서 종류(이력서/채용공고).
            format: 입력 형식(PDF/URL/TEXT 등).
            file_name: 업로드 원본 파일명(파일 입력일 때).
            file_path: 저장된 파일 경로(파일 입력일 때).
            content_type: 파일 MIME 타입(파일 입력일 때).
            source_url: 채용공고 URL(URL 입력일 때).
            extracted_text: 미리 확보된 본문 텍스트(텍스트 입력일 때).

        Returns:
            생성된 Document 레코드.
        """
        async with self._session_factory() as session:
            record = Document(
                document_type=document_type,
                format=format.value,
                file_name=file_name,
                file_path=file_path,
                content_type=content_type,
                source_url=source_url,
                extracted_text=extracted_text,
                status=ParseStatus.PENDING,
            )
            session.add(record)
            await session.commit()
            return record

    async def get(self, document_id: int) -> Document | None:
        """ID로 문서 레코드를 조회한다.

        Args:
            document_id: 조회할 문서 ID.

        Returns:
            문서가 있으면 Document, 없으면 None.
        """
        async with self._session_factory() as session:
            return await session.get(Document, document_id)

    async def mark_started(self, document_id: int) -> None:
        """문서 상태를 STARTED로 표시한다(문서가 없으면 무시).

        Args:
            document_id: 상태를 변경할 문서 ID.
        """
        async with self._session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                return
            document.status = ParseStatus.STARTED
            await session.commit()

    async def mark_done(self, document_id: int, *, extracted_text: str, metadata: dict) -> None:
        """문서를 DONE으로 표시하고 추출 결과를 저장한다(문서가 없으면 무시).

        Args:
            document_id: 상태를 변경할 문서 ID.
            extracted_text: 저장할 추출 본문 텍스트.
            metadata: 저장할 추출 메타데이터.
        """
        async with self._session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                return
            document.status = ParseStatus.DONE
            document.extracted_text = extracted_text
            document.extracted_metadata = metadata
            await session.commit()

    async def mark_failed(self, document_id: int, *, error: str) -> None:
        """문서를 FAILED로 표시하고 오류 메시지를 저장한다(문서가 없으면 무시).

        Args:
            document_id: 상태를 변경할 문서 ID.
            error: 사용자에게 보여줄 실패 사유.
        """
        async with self._session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                return
            document.status = ParseStatus.FAILED
            document.error = error
            await session.commit()
