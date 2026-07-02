import asyncio
from collections.abc import Callable

from dependency_injector.wiring import Provide, inject

from app.celery_app import celery_app
from app.config.containers import Container
from app.database.session import Database
from app.repositories.documents import DocumentsRepository
from app.repositories.profiles import ProfilesRepository
from app.services.document import DocumentService


@celery_app.task(name="documents.parse")
def task_parse_document(document_id: int, user_id: int) -> None:
    """문서 파싱 Celery 태스크 진입점. 비동기 파싱을 동기 워커에서 실행한다.

    Args:
        document_id: 파싱할 문서의 ID.
        user_id: 문서를 업로드한 사용자 ID(이력서 프로필 저장용).
    """
    asyncio.run(_parse_document(document_id, user_id))


@inject
async def _parse_document(
    document_id: int,
    user_id: int,
    database: Database = Provide[Container.worker_database],
    build_document_service: Callable[..., DocumentService] = Provide[Container.document_service.provider],
) -> None:
    """워커용 DB/레포지토리로 서비스를 구성해 문서 파싱을 수행한다.

    Args:
        document_id: 파싱할 문서의 ID.
        user_id: 문서를 업로드한 사용자 ID(이력서 프로필 저장용).
        database: 컨테이너가 주입하는 워커 전용 Database(태스크마다 새로 생성).
        build_document_service: 컨테이너의 document_service provider. 레포지토리만
            워커 세션 기반으로 덮어써서 서비스를 만든다.
    """
    async with database:
        # 워커는 worker_database(Factory)로 세션을 만들어야 해서 repo는 직접 구성하고,
        # crawler/classifier 배선은 컨테이너의 document_service provider에 위임한다.
        document_service = build_document_service(
            documents_repository=DocumentsRepository(session_factory=database.async_session),
            profiles_repository=ProfilesRepository(session_factory=database.async_session),
        )
        await document_service.process(document_id, user_id)
