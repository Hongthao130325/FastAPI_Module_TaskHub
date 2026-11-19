from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.core.messages import (
    PROJECT_NOT_FOUND_MESSAGE,
    PROJECT_UPDATE_EMPTY_MESSAGE,
    RESOURCE_CONFLICT_MESSAGE,
    WORKSPACE_ACCESS_FORBIDDEN_MESSAGE,
    WORKSPACE_NOT_FOUND_MESSAGE,
)
from app.core.permissions import has_workspace_role
from app.models.enums import UserRole, WorkspaceRole
from app.models.project import Project
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.workspace_repository import WorkspaceRepository

T = TypeVar("T")


class ProjectService:
    def __init__(
        self,
        session: AsyncSession,
        repository: ProjectRepository,
        workspace_repository: WorkspaceRepository,
    ):
        self.session = session
        self.repository = repository
        self.workspace_repository = workspace_repository

    async def _execute_write(
        self,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        try:
            result = await operation()
            await self.session.commit()

            return result

        except IntegrityError as exc:
            await self.session.rollback()

            raise ConflictException(RESOURCE_CONFLICT_MESSAGE) from exc

    async def _ensure_workspace_access(
        self,
        workspace_id: int,
        user: User,
        allowed_roles: set[WorkspaceRole],
    ):
        workspace = await self.workspace_repository.get_by_id(workspace_id)

        if workspace is None:
            raise NotFoundException(WORKSPACE_NOT_FOUND_MESSAGE)

        membership = await self.workspace_repository.get_membership(
            workspace_id,
            user.id,
        )

        if not has_workspace_role(user, membership, allowed_roles):
            raise ForbiddenException(WORKSPACE_ACCESS_FORBIDDEN_MESSAGE)

        return workspace

    async def _get_project(self, project_id: int) -> Project:
        project = await self.repository.get_by_id(project_id)

        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND_MESSAGE)

        return project

    async def _ensure_project_access(
        self,
        project_id: int,
        user: User,
        allowed_roles: set[WorkspaceRole],
    ) -> Project:
        project = await self._get_project(project_id)

        await self._ensure_workspace_access(
            project.workspace_id,
            user,
            allowed_roles,
        )

        return project

    async def create_project(
        self,
        workspace_id: int,
        name: str,
        description: str | None,
        user: User,
    ) -> Project:
        await self._ensure_workspace_access(
            workspace_id,
            user,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )

        project = Project(
            workspace_id=workspace_id,
            name=name,
            description=description,
        )

        await self._execute_write(lambda: self.repository.create(project))
        await self.session.refresh(project)

        return project

    async def get_all_projects(self, user: User) -> list[Project]:
        if user.role == UserRole.ADMIN:
            return await self.repository.get_all()

        return await self.repository.get_all_for_user(user.id)

    async def get_projects_by_workspace(
        self,
        workspace_id: int,
        user: User,
    ) -> list[Project]:
        await self._ensure_workspace_access(
            workspace_id,
            user,
            {
                WorkspaceRole.OWNER,
                WorkspaceRole.EDITOR,
                WorkspaceRole.VIEWER,
            },
        )

        return await self.repository.get_all_for_workspace(workspace_id)

    async def get_project_by_id(
        self,
        project_id: int,
        user: User,
    ) -> Project:
        return await self._ensure_project_access(
            project_id,
            user,
            {
                WorkspaceRole.OWNER,
                WorkspaceRole.EDITOR,
                WorkspaceRole.VIEWER,
            },
        )

    async def update_project(
        self,
        project_id: int,
        update_data: dict,
        user: User,
    ) -> Project:
        project = await self._ensure_project_access(
            project_id,
            user,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )

        if not update_data:
            raise BadRequestException(PROJECT_UPDATE_EMPTY_MESSAGE)

        await self._execute_write(lambda: self.repository.update(project, update_data))
        await self.session.refresh(project)

        return project

    async def archive_project(
        self,
        project_id: int,
        user: User,
    ) -> Project:
        project = await self._ensure_project_access(
            project_id,
            user,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        )

        await self._execute_write(lambda: self.repository.archive(project))
        await self.session.refresh(project)

        return project
