import contextlib
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import settings


class Database:
    def __init__(self, *, pool_size: int = 5, max_overflow: int = 10) -> None:
        """비동기 엔진과 세션 팩토리를 생성한다.

        Args:
            pool_size: 커넥션 풀의 기본 연결 수.
            max_overflow: 풀을 초과해 추가로 열 수 있는 연결 수.
        """
        self._engine = create_async_engine(settings.DATABASE_URL, pool_size=pool_size, max_overflow=max_overflow)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    async def __aenter__(self) -> "Database":
        """async with 진입 시 자기 자신을 반환한다.

        Returns:
            현재 Database 인스턴스.
        """
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """async with 종료 시 엔진을 정리한다.

        Args:
            exc_type: 발생한 예외의 타입(없으면 None).
            exc: 발생한 예외 객체(없으면 None).
            tb: 트레이스백(없으면 None).
        """
        await self.dispose()

    @contextlib.asynccontextmanager
    async def async_session(self) -> AsyncIterator[AsyncSession]:
        """비동기 DB 세션을 열어 컨텍스트로 제공한다.

        Yields:
            요청 범위 동안 사용할 AsyncSession.
        """
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        """엔진과 커넥션 풀을 해제한다."""
        await self._engine.dispose()
