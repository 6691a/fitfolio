from redis.asyncio import Redis, from_url

from app.config.settings import settings


class RedisCache:
    def __init__(self) -> None:
        """설정의 REDIS_URL로 비동기 Redis 클라이언트를 생성한다."""
        self._client: Redis = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    @property
    def client(self) -> Redis:
        """내부 비동기 Redis 클라이언트를 반환한다.

        Returns:
            연결 풀이 연결된 Redis 클라이언트.
        """
        return self._client

    async def dispose(self) -> None:
        """Redis 클라이언트와 연결 풀을 닫는다."""
        await self._client.aclose()
