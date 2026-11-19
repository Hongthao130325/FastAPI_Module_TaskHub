from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.repositories.project_repository import ProjectRepository
from app.repositories.reference_repository import ReferenceRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.auth_service import AuthService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.workspace_service import WorkspaceService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_task_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskService:
    task_repository = TaskRepository(session)
    reference_repository = ReferenceRepository(session)
    workspace_repository = WorkspaceRepository(session)

    return TaskService(
        session=session,
        repository=task_repository,
        reference_repository=reference_repository,
        workspace_repository=workspace_repository,
    )


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    user_repository = UserRepository(session)
    refresh_token_repository = RefreshTokenRepository(session)

    return AuthService(
        session=session,
        repository=user_repository,
        refresh_token_repository=refresh_token_repository,
    )


def get_workspace_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceService:
    workspace_repository = WorkspaceRepository(session)
    user_repository = UserRepository(session)

    return WorkspaceService(
        session=session,
        repository=workspace_repository,
        user_repository=user_repository,
    )


def get_project_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectService:
    project_repository = ProjectRepository(session)
    workspace_repository = WorkspaceRepository(session)

    return ProjectService(
        session=session,
        repository=project_repository,
        workspace_repository=workspace_repository,
    )
