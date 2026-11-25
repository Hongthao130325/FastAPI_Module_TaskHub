import json
from typing import Any

from redis.asyncio import Redis

from app.core.constants import CACHE_DEFAULT_TTL_SECONDS
from app.core.messages import CACHE_TTL_INVALID_MESSAGE


class CacheService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> Any | None:
        cached_value = await self.redis.get(key)

        if cached_value is None:
            return None

        return json.loads(cached_value)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = CACHE_DEFAULT_TTL_SECONDS,
    ) -> bool:
        if ttl <= 0:
            raise ValueError(CACHE_TTL_INVALID_MESSAGE)

        serialized_value = json.dumps(value, ensure_ascii=False)

        return await self.redis.set(
            key,
            serialized_value,
            ex=ttl,
        )

    async def delete(self, key: str) -> int:
        return await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        keys = [key async for key in self.redis.scan_iter(match=pattern)]

        if not keys:
            return 0

        return await self.redis.unlink(*keys)
