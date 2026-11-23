from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.session import AsyncSessionLocal
from app.repositories.comment_repository import CommentRepository
from app.repositories.label_repository import LabelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.reference_repository import ReferenceRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.pagination import PaginationParams
from app.services.auth_service import AuthService
from app.services.comment_service import CommentService
from app.services.label_service import LabelService
from app.services.project_service import ProjectService
from app.services.task_authorization import TaskAuthorization
from app.services.task_service import TaskService
from app.services.workspace_authorization import WorkspaceAuthorization
from app.services.workspace_service import WorkspaceService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_task_authorization(
    session: AsyncSession,
) -> TaskAuthorization:
    return TaskAuthorization(
        task_repository=TaskRepository(session),
        project_repository=ProjectRepository(session),
        workspace_repository=WorkspaceRepository(session),
    )


def get_task_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskService:
    authorization = get_task_authorization(session)
    reference_repository = ReferenceRepository(session)

    return TaskService(
        session=session,
        repository=authorization.task_repository,
        reference_repository=reference_repository,
        workspace_repository=authorization.workspace_repository,
        authorization=authorization,
    )


def get_label_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LabelService:
    return LabelService(
        session=session,
        repository=LabelRepository(session),
        authorization=get_task_authorization(session),
    )


def get_comment_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CommentService:
    return CommentService(
        session=session,
        repository=CommentRepository(session),
        authorization=get_task_authorization(session),
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

    authorization = WorkspaceAuthorization(workspace_repository)

    return WorkspaceService(
        session=session,
        repository=workspace_repository,
        user_repository=user_repository,
        authorization=authorization,
    )


def get_project_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectService:
    project_repository = ProjectRepository(session)
    workspace_repository = WorkspaceRepository(session)

    authorization = get_task_authorization(session)
    workspace_authorization = WorkspaceAuthorization(workspace_repository)

    return ProjectService(
        session=session,
        repository=project_repository,
        authorization=authorization,
        workspace_authorization=workspace_authorization,
    )


def get_pagination(
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PaginationParams:
    return PaginationParams(
        page=page,
        limit=limit,
    )


PaginationDep = Annotated[
    PaginationParams,
    Depends(get_pagination),
]
