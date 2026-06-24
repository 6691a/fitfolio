import contextlib
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import settings


class Database:
    def __init__(self, *, pool_size: int = 5, max_overflow: int = 10) -> None:
        self._engine = create_async_engine(settings.DATABASE_URL, pool_size=pool_size, max_overflow=max_overflow)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    @contextlib.asynccontextmanager
    async def async_session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        await self._engine.dispose()
