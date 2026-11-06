from fastapi import FastAPI

from app.core.lifespan import lifespan
from app.api.v1.router import api_router


app = FastAPI(
    title="TaskHub",
    description="Task Management API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to TaskHub"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "TaskHub"
    }