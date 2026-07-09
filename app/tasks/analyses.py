import asyncio
from collections.abc import Callable

from dependency_injector.wiring import Provide, inject

from app.celery_app import celery_app
from app.config.containers import Container
from app.database.session import Database
from app.repositories.analyses import AnalysesRepository
from app.repositories.preferences import PreferencesRepository
from app.repositories.profiles import ProfilesRepository
from app.repositories.user_profiles import UserProfilesRepository
from app.services.analysis import AnalysisService


@celery_app.task(name="analyses.run")
def task_analyze_fit(analysis_id: int) -> None:
    """적합도 분석 Celery 태스크 진입점. 비동기 분석을 동기 워커에서 실행한다.

    Args:
        analysis_id: 실행할 분석 ID.
    """
    asyncio.run(_analyze_fit(analysis_id))


@inject
async def _analyze_fit(
    analysis_id: int,
    database: Database = Provide[Container.worker_database],
    build_analysis_service: Callable[..., AnalysisService] = Provide[Container.analysis_service.provider],
) -> None:
    """워커용 DB/레포지토리로 서비스를 구성해 적합도 분석을 수행한다.

    Args:
        analysis_id: 실행할 분석 ID.
        database: 컨테이너가 주입하는 워커 전용 Database(태스크마다 새로 생성).
        build_analysis_service: 컨테이너의 analysis_service provider. 레포지토리만
            워커 세션 기반으로 덮어써서 서비스를 만든다.
    """
    async with database:
        analysis_service = build_analysis_service(
            analyses_repository=AnalysesRepository(session_factory=database.async_session),
            profiles_repository=ProfilesRepository(session_factory=database.async_session),
            preferences_repository=PreferencesRepository(session_factory=database.async_session),
            user_profiles_repository=UserProfilesRepository(session_factory=database.async_session),
        )
        await analysis_service.run(analysis_id)
