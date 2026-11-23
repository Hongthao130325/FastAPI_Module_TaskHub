import asyncio

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis

from app.services.cache_service import CacheService


@pytest_asyncio.fixture
async def cache_service():
    redis = FakeRedis(decode_responses=True)

    try:
        yield CacheService(redis)
    finally:
        await redis.aclose()


@pytest.mark.asyncio
async def test_set_and_get_cache(cache_service):
    value = {
        "id": 1,
        "name": "TaskHub",
        "tags": ["fastapi", "redis"],
    }

    result = await cache_service.set("project:1", value)

    assert result is True
    assert await cache_service.get("project:1") == value


@pytest.mark.asyncio
async def test_get_returns_none_when_cache_does_not_exist(cache_service):
    result = await cache_service.get("missing:key")

    assert result is None


@pytest.mark.asyncio
async def test_set_cache_with_custom_ttl(cache_service):
    await cache_service.set("temporary:key", {"value": 1}, ttl=60)

    ttl = await cache_service.redis.ttl("temporary:key")

    assert 0 < ttl <= 60


@pytest.mark.asyncio
async def test_set_rejects_non_positive_ttl(cache_service):
    with pytest.raises(ValueError, match="TTL must be greater than zero"):
        await cache_service.set("invalid:key", {"value": 1}, ttl=0)


@pytest.mark.asyncio
async def test_delete_cache(cache_service):
    await cache_service.set("task:1", {"id": 1})

    deleted_count = await cache_service.delete("task:1")

    assert deleted_count == 1
    assert await cache_service.get("task:1") is None


@pytest.mark.asyncio
async def test_delete_pattern(cache_service):
    await cache_service.set("task:1", {"id": 1})
    await cache_service.set("task:2", {"id": 2})
    await cache_service.set("project:1", {"id": 1})

    deleted_count = await cache_service.delete_pattern("task:*")

    assert deleted_count == 2
    assert await cache_service.get("task:1") is None
    assert await cache_service.get("task:2") is None
    assert await cache_service.get("project:1") == {"id": 1}


@pytest.mark.asyncio
async def test_get_returns_none_after_cache_expiration(cache_service):
    await cache_service.set("expired:key", {"value": 1}, ttl=1)

    await asyncio.sleep(1.1)

    assert await cache_service.get("expired:key") is None
