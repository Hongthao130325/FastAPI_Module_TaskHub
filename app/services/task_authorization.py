from dataclasses import dataclass

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.core.messages import (
    PROJECT_ARCHIVED_MESSAGE,
    PROJECT_NOT_FOUND_MESSAGE,
    TASK_ACCESS_FORBIDDEN_MESSAGE,
    TASK_NOT_FOUND_MESSAGE,
)
from app.core.permissions import has_workspace_role
from app.models.enums import ProjectStatus, WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_repository import WorkspaceRepository


@dataclass
class ProjectAccessContext:
    project: Project
    membership: WorkspaceMember | None


@dataclass
class TaskAccessContext:
    task: Task
    project: Project
    membership: WorkspaceMember | None


class TaskAuthorization:
    def __init__(
        self,
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        workspace_repository: WorkspaceRepository,
    ):
        self.task_repository = task_repository
        self.project_repository = project_repository
        self.workspace_repository = workspace_repository

    async def get_project_context(
        self,
        project_id: int,
        user: User,
    ) -> ProjectAccessContext:
        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND_MESSAGE)

        membership = await self.workspace_repository.get_membership(
            project.workspace_id,
            user.id,
        )

        if not has_workspace_role(
            user,
            membership,
            {
                WorkspaceRole.OWNER,
                WorkspaceRole.EDITOR,
                WorkspaceRole.VIEWER,
            },
        ):
            raise NotFoundException(PROJECT_NOT_FOUND_MESSAGE)

        return ProjectAccessContext(
            project=project,
            membership=membership,
        )

    async def get_task_context(
        self,
        task_id: int,
        user: User,
    ) -> TaskAccessContext:
        task = await self.task_repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

        try:
            project_context = await self.get_project_context(
                task.project_id,
                user,
            )
        except NotFoundException:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE) from None

        return TaskAccessContext(
            task=task,
            project=project_context.project,
            membership=project_context.membership,
        )

    @staticmethod
    def ensure_write_access(
        context: ProjectAccessContext | TaskAccessContext,
        user: User,
    ) -> None:
        if not has_workspace_role(
            user,
            context.membership,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        ):
            raise ForbiddenException(TASK_ACCESS_FORBIDDEN_MESSAGE)

        if context.project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(PROJECT_ARCHIVED_MESSAGE)
