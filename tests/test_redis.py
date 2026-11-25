import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI

import app.core.lifespan as lifespan_module
from app.core.config import settings


def test_lifespan_connects_and_closes_redis(monkeypatch):
    redis_client = AsyncMock()
    redis_factory = Mock(return_value=redis_client)
    dispose = AsyncMock()

    monkeypatch.setattr(
        lifespan_module.Redis,
        "from_url",
        redis_factory,
    )
    monkeypatch.setattr(
        lifespan_module,
        "engine",
        SimpleNamespace(dispose=dispose),
    )

    async def run_lifespan():
        app = FastAPI()

        async with lifespan_module.lifespan(app):
            assert app.state.redis is redis_client
            redis_client.ping.assert_awaited_once()

        redis_client.aclose.assert_awaited_once()
        dispose.assert_awaited_once()

    asyncio.run(run_lifespan())

    redis_factory.assert_called_once_with(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    )


def test_lifespan_closes_resources_when_redis_ping_fails(monkeypatch):
    redis_client = AsyncMock()
    redis_client.ping.side_effect = ConnectionError("Redis unavailable")

    monkeypatch.setattr(
        lifespan_module.Redis,
        "from_url",
        Mock(return_value=redis_client),
    )

    dispose = AsyncMock()
    monkeypatch.setattr(
        lifespan_module,
        "engine",
        SimpleNamespace(dispose=dispose),
    )

    async def run_lifespan():
        app = FastAPI()

        with pytest.raises(ConnectionError, match="Redis unavailable"):
            async with lifespan_module.lifespan(app):
                pass

        redis_client.aclose.assert_awaited_once()
        dispose.assert_awaited_once()

    asyncio.run(run_lifespan())
