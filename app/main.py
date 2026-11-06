from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.exception_handlers import not_found_exception_handler
from app.core.exceptions import NotFoundException
from app.core.lifespan import lifespan

app = FastAPI(
    title="TaskHub",
    description="Task Management API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_exception_handler(NotFoundException, not_found_exception_handler)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Welcome to TaskHub"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "TaskHub"}
