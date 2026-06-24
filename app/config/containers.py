from dependency_injector import containers, providers

from app.config.settings import Settings
from app.database.session import Database
from app.repositories.documents import DocumentsRepository
from app.repositories.profiles import ProfilesRepository
from app.services.document import DocumentService


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(Settings)

    database = providers.Singleton(Database)

    # Must stay a Factory, not a Singleton: asyncpg's connection pool can't be
    # reused safely across the separate event loops each Celery asyncio.run() creates.
    worker_database = providers.Factory(Database, pool_size=1, max_overflow=0)

    documents_repository = providers.Factory(
        DocumentsRepository,
        session_factory=database.provided.async_session,
    )

    profiles_repository = providers.Factory(
        ProfilesRepository,
        session_factory=database.provided.async_session,
    )

    document_service = providers.Factory(
        DocumentService,
        documents_repository=documents_repository,
    )
