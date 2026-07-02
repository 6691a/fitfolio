from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class UsersRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        """사용자 영속화에 사용할 세션 팩토리를 보관한다.

        Args:
            session_factory: 비동기 DB 세션을 여는 컨텍스트 매니저 팩토리.
        """
        self._session_factory = session_factory

    async def create(self, *, email: str, hashed_password: str, nickname: str) -> User:
        """새 사용자를 생성한다.

        Args:
            email: 사용자 이메일.
            hashed_password: 해시된 비밀번호.
            nickname: 사용자 닉네임.

        Returns:
            생성된 User 레코드.
        """
        async with self._session_factory() as session:
            user = User(email=email, hashed_password=hashed_password, nickname=nickname)
            session.add(user)
            await session.commit()
            return user

    async def get(self, user_id: int) -> User | None:
        """ID로 사용자를 조회한다.

        Args:
            user_id: 조회할 사용자 ID.

        Returns:
            사용자가 있으면 User, 없으면 None.
        """
        async with self._session_factory() as session:
            return await session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        """이메일로 사용자를 조회한다.

        Args:
            email: 조회할 이메일.

        Returns:
            사용자가 있으면 User, 없으면 None.
        """
        async with self._session_factory() as session:
            return await session.scalar(select(User).where(User.email == email))

    async def get_by_nickname(self, nickname: str) -> User | None:
        """닉네임으로 사용자를 조회한다.

        Args:
            nickname: 조회할 닉네임.

        Returns:
            사용자가 있으면 User, 없으면 None.
        """
        async with self._session_factory() as session:
            return await session.scalar(select(User).where(User.nickname == nickname))
