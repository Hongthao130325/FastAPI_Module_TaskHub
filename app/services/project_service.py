from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
)
from app.core.messages import (
    PROJECT_ACCESS_FORBIDDEN_MESSAGE,
    PROJECT_MODIFICATION_ARCHIVED_MESSAGE,
    PROJECT_UPDATE_EMPTY_MESSAGE,
)
from app.models.enums import UserRole, WorkspaceRole
from app.models.project import Project
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.services.task_authorization import TaskAuthorization
from app.services.transaction import execute_write
from app.services.workspace_authorization import WorkspaceAuthorization


class ProjectService:
    def __init__(
        self,
        session: AsyncSession,
        repository: ProjectRepository,
        authorization: TaskAuthorization,
        workspace_authorization: WorkspaceAuthorization,
    ):
        self.session = session
        self.repository = repository
        self.authorization = authorization
        self.workspace_authorization = workspace_authorization

    async def _ensure_workspace_access(
        self,
        workspace_id: int,
        user: User,
        allowed_roles: set[WorkspaceRole],
    ):
        context = await self.workspace_authorization.get_workspace_context(
            workspace_id,
            user,
        )
        self.workspace_authorization.ensure_role_access(
            context,
            user,
            allowed_roles,
        )

        return context.workspace

    async def _ensure_project_access(
        self,
        project_id: int,
        user: User,
        allowed_roles: set[WorkspaceRole],
    ) -> Project:
        context = await self.authorization.get_project_context(
            project_id,
            user,
        )
        self.authorization.ensure_role_access(
            context,
            user,
            allowed_roles,
            PROJECT_ACCESS_FORBIDDEN_MESSAGE,
        )

        return context.project

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

        await execute_write(self.session, lambda: self.repository.create(project))
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
        context = await self.authorization.get_project_context(
            project_id,
            user,
        )
        self.authorization.ensure_write_access(
            context,
            user,
            PROJECT_ACCESS_FORBIDDEN_MESSAGE,
            archived_message=PROJECT_MODIFICATION_ARCHIVED_MESSAGE,
        )
        project = context.project

        if not update_data:
            raise BadRequestException(PROJECT_UPDATE_EMPTY_MESSAGE)

        await execute_write(
            self.session, lambda: self.repository.update(project, update_data)
        )
        await self.session.refresh(project)

        return project

    async def archive_project(
        self,
        project_id: int,
        user: User,
    ) -> Project:
        context = await self.authorization.get_project_context(
            project_id,
            user,
        )
        self.authorization.ensure_write_access(
            context,
            user,
            PROJECT_ACCESS_FORBIDDEN_MESSAGE,
            archived_message=PROJECT_MODIFICATION_ARCHIVED_MESSAGE,
        )
        project = context.project

        await execute_write(self.session, lambda: self.repository.archive(project))
        await self.session.refresh(project)

        return project
