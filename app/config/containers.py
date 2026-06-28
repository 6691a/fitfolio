from dependency_injector import containers, providers

from app.ai.classification.document import LangChainDocumentClassifier
from app.cache.redis import RedisCache
from app.config.settings import Settings
from app.crawlers.job_postings import JobPostingCrawler
from app.crawlers.saramin import SaraminJobPostingCrawler
from app.crawlers.wanted import WantedJobPostingCrawler
from app.database.session import Database
from app.repositories.documents import DocumentsRepository
from app.repositories.profiles import ProfilesRepository
from app.services.document import DocumentService


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(Settings)

    database = providers.Singleton(Database)

    cache = providers.Singleton(RedisCache)

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

    wanted_job_posting_crawler = providers.Factory(WantedJobPostingCrawler)
    saramin_job_posting_crawler = providers.Factory(SaraminJobPostingCrawler)
    job_posting_crawler = providers.Factory(
        JobPostingCrawler,
        crawlers=providers.List(
            wanted_job_posting_crawler,
            saramin_job_posting_crawler,
        ),
    )
    document_classifier = providers.Factory(LangChainDocumentClassifier)

    document_service = providers.Factory(
        DocumentService,
        documents_repository=documents_repository,
        profiles_repository=profiles_repository,
        job_posting_crawler=job_posting_crawler,
        document_classifier=document_classifier,
    )
