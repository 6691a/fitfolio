from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.schemas.documents import DocumentFormat, DocumentKind, ParseStatus

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(frozen=True)
class UrlDocumentRequestResult:
    """URL 문서 요청 결과.

    Attributes:
        document: 생성했거나 재사용하기로 한 문서.
        created: 이번 요청에서 새로 생성했으면 True, 기존 문서 재사용이면 False.
    """

    document: Document
    created: bool


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
        user_id: int | None = None,
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
            user_id: 문서를 업로드한 사용자 ID.
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
                user_id=user_id,
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

    async def find_reusable_by_source_url(self, *, document_type: DocumentKind, source_url: str) -> Document | None:
        """같은 source_url로 재사용 가능한 URL 문서를 찾는다.

        PENDING/STARTED/RETRY는 이미 처리 중인 문서이므로 새 레코드를 만들지 않고
        기존 document_id를 반환한다. DONE은 완료 결과를 재사용한다. FAILED는 재시도를
        허용하기 위해 제외한다.

        Args:
            document_type: 문서 종류(이력서/채용공고).
            source_url: 정규화된 원본 URL.

        Returns:
            가장 최근의 재사용 가능한 동일 URL 문서, 없으면 None.
        """
        async with self._session_factory() as session:
            return await session.scalar(
                select(Document)
                .where(
                    Document.document_type == document_type.value,
                    Document.format == DocumentFormat.URL.value,
                    Document.source_url == source_url,
                    Document.status.in_(
                        [
                            ParseStatus.PENDING,
                            ParseStatus.STARTED,
                            ParseStatus.RETRY,
                            ParseStatus.DONE,
                        ]
                    ),
                )
                .order_by(Document.id.desc())
                .limit(1)
            )

    async def create_url_or_get_reusable(
        self, *, document_type: DocumentKind, source_url: str
    ) -> UrlDocumentRequestResult:
        """URL 문서를 원자적으로 생성하거나 이미 처리 중/완료된 동일 URL 문서를 반환한다.

        DB의 partial unique index가 동시 생성 경쟁을 막는다. 경쟁에서 진 요청은
        IntegrityError 후 재조회해 먼저 생성된 문서 ID를 재사용한다.

        Args:
            document_type: 문서 종류(보통 채용공고).
            source_url: 정규화된 원본 URL.

        Returns:
            문서와 신규 생성 여부.

        Raises:
            IntegrityError: unique 충돌 후에도 재사용 가능한 문서를 찾지 못한 경우.
        """
        existing = await self.find_reusable_by_source_url(document_type=document_type, source_url=source_url)
        if existing is not None:
            return UrlDocumentRequestResult(document=existing, created=False)

        async with self._session_factory() as session:
            record = Document(
                user_id=None,
                document_type=document_type,
                format=DocumentFormat.URL.value,
                source_url=source_url,
                status=ParseStatus.PENDING,
            )
            session.add(record)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await self.find_reusable_by_source_url(document_type=document_type, source_url=source_url)
                if existing is not None:
                    return UrlDocumentRequestResult(document=existing, created=False)
                raise
            return UrlDocumentRequestResult(document=record, created=True)

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
