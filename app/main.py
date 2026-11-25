from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exception_handlers import app_exception_handler
from app.core.exceptions import ApplicationError
from app.core.lifespan import lifespan
from app.core.logging import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware

configure_logging(settings.LOG_LEVEL)


app = FastAPI(
    title="TaskHub",
    summary="Workspace-based task management API",
    description=(
        "TaskHub is a REST API for collaborative task management.\n\n"
        "## Core features\n"
        "- User registration, authentication, and token refresh.\n"
        "- Workspaces, memberships, and role-based access control.\n"
        "- Projects, tasks, labels, and comments.\n"
        "- Redis-backed caching and request logging.\n\n"
        "## Authentication\n"
        "Protected endpoints require a Bearer access token. "
        "Register or log in through the Authentication endpoints "
        "to obtain tokens.\n\n"
        "## Authorization\n"
        "Access to resources is scoped to workspace membership. "
        "Workspace roles determine which operations are permitted.\n\n"
        "## Pagination\n"
        "List endpoints that support pagination accept page and limit "
        "query parameters. Check each endpoint for its defaults and limits."
    ),
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": (
                "User registration, login, token refresh, logout, and "
                "password management."
            ),
        },
        {
            "name": "Workspaces",
            "description": "Create and manage workspaces and their members.",
        },
        {
            "name": "Projects",
            "description": "Manage projects within accessible workspaces.",
        },
        {
            "name": "Tasks",
            "description": "Create, retrieve, update, and delete project tasks.",
        },
        {
            "name": "Labels",
            "description": "Manage project labels and attach them to tasks.",
        },
        {
            "name": "Comments",
            "description": "Create and manage comments associated with tasks.",
        },
    ],
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_exception_handler(ApplicationError, app_exception_handler)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(api_router)


@app.get(
    "/",
    summary="API welcome endpoint",
    description="Returns a welcome message for the TaskHub API.",
)
async def root():
    return {"message": "Welcome to TaskHub"}


@app.get(
    "/health",
    summary="Health check",
    description="Checks whether the TaskHub API process is responding.",
)
async def health_check():
    return {"status": "healthy", "service": "TaskHub"}
