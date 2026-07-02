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
from app.repositories.users import UsersRepository
from app.services.auth import AuthService
from app.services.document import DocumentService
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler


def build_langfuse_handler(settings: Settings) -> CallbackHandler | None:
    """Settings의 키로 전역 Langfuse client를 초기화한 뒤 LangChain 핸들러를 만든다.

    CallbackHandler(v4)는 자격증명을 직접 받지 않고 전역 client를 쓴다. pydantic Settings는
    .env를 os.environ이 아닌 Settings 객체에만 싣기 때문에, 여기서 명시적으로 client를 만들어야
    로컬 실행에서도 트레이싱이 동작한다.

    Args:
        settings: Langfuse 키/호스트가 담긴 설정.

    Returns:
        키가 모두 있으면 CallbackHandler, 하나라도 비면 None(트레이싱 비활성).
    """
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return None
    Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_BASE_URL,
    )
    return CallbackHandler()


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(Settings)

    database = providers.Singleton(Database)

    cache = providers.Singleton(RedisCache)

    langfuse_handler = providers.Singleton(build_langfuse_handler, settings)

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

    users_repository = providers.Factory(
        UsersRepository,
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

    auth_service = providers.Factory(
        AuthService,
        users_repository=users_repository,
        settings=settings,
    )
