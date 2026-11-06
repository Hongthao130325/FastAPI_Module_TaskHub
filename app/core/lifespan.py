from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("TaskHub is starting...")

    yield

    print("TaskHub is shutting down...")