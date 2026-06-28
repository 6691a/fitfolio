import pytest

from app.database import session as session_module


class FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


@pytest.mark.asyncio
async def test_database_async_context_manager_disposes_engine(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(session_module, "create_async_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(session_module, "async_sessionmaker", lambda *args, **kwargs: object())

    database = session_module.Database()

    async with database as entered:
        assert entered is database

    assert engine.disposed is True
