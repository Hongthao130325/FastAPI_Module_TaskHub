import json
from typing import Any

from redis.asyncio import Redis


class CacheService:
    DEFAULT_TTL = 300

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
        ttl: int = DEFAULT_TTL,
    ) -> bool:
        if ttl <= 0:
            raise ValueError("Cache TTL must be greater than zero.")

        serialized_value = json.dumps(value, ensure_ascii=False)

        return await self.redis.set(
            key,
            serialized_value,
            ex=ttl,
        )

    async def delete(self, key: str) -> int:
        return await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        deleted_count = 0

        async for key in self.redis.scan_iter(match=pattern):
            deleted_count += await self.redis.delete(key)

        return deleted_count
