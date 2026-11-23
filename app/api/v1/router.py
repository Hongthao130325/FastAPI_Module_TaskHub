from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    comments,
    labels,
    projects,
    tasks,
    workspaces,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(tasks.project_tasks_router)
api_router.include_router(tasks.router)
api_router.include_router(workspaces.router)
api_router.include_router(projects.router)
api_router.include_router(labels.router)
api_router.include_router(comments.router)
