import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.core.config import settings
from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TaskHub is starting...")

    redis_client = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    )
    app.state.redis = redis_client

    try:
        await redis_client.ping()
        logger.info("Redis connection established.")

        yield
    finally:
        try:
            await redis_client.aclose()
            logger.info("Redis connection closed.")
        finally:
            await engine.dispose()
            logger.info("TaskHub is shutting down.")
