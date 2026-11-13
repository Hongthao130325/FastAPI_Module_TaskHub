import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TaskHub is starting...")

    yield

    await engine.dispose()

    logger.info("TaskHub is shutting down...")
