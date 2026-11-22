from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.core.messages import (
    PROJECT_ACCESS_FORBIDDEN_MESSAGE,
    PROJECT_NOT_FOUND_MESSAGE,
    RESOURCE_CONFLICT_MESSAGE,
    TASK_NOT_FOUND_MESSAGE,
    USER_NOT_FOUND_MESSAGE,
)
from app.core.permissions import has_workspace_role
from app.models.enums import ProjectStatus, UserRole, WorkspaceRole
from app.models.task import Task
from app.models.user import User
from app.repositories.reference_repository import ReferenceRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.task import TaskCreate

T = TypeVar("T")


class TaskService:
    def __init__(
        self,
        session: AsyncSession,
        repository: TaskRepository,
        reference_repository: ReferenceRepository,
        workspace_repository: WorkspaceRepository,
    ):
        self.session = session
        self.repository = repository
        self.reference_repository = reference_repository
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

    async def _get_task_workspace_context(
        self,
        task: Task,
        user: User,
    ):
        project = await self.reference_repository.get_project(task.project_id)

        if project is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

        membership = await self.workspace_repository.get_membership(
            workspace_id=project.workspace_id,
            user_id=user.id,
        )

        if user.role.value != "ADMIN" and membership is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

        return project, membership

    async def _ensure_task_view_access(
        self,
        task: Task,
        user: User,
    ) -> None:
        project, membership = await self._get_task_workspace_context(task, user)

        if not has_workspace_role(
            user,
            membership,
            {
                WorkspaceRole.OWNER,
                WorkspaceRole.EDITOR,
                WorkspaceRole.VIEWER,
            },
        ):
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

    async def _ensure_task_write_access(
        self,
        task: Task,
        user: User,
    ) -> None:
        project, membership = await self._get_task_workspace_context(task, user)

        if not has_workspace_role(
            user,
            membership,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        ):
            raise ForbiddenException(PROJECT_ACCESS_FORBIDDEN_MESSAGE)

        if project.status == ProjectStatus.ARCHIVED:
            raise ForbiddenException(PROJECT_ACCESS_FORBIDDEN_MESSAGE)

    async def _validate_assignee(
        self,
        workspace_id: int,
        assignee_id: int | None,
    ) -> None:
        if assignee_id is None:
            return

        if not await self.reference_repository.user_exists(assignee_id):
            raise NotFoundException(USER_NOT_FOUND_MESSAGE)

        membership = await self.workspace_repository.get_membership(
            workspace_id=workspace_id,
            user_id=assignee_id,
        )

        if membership is None:
            raise ForbiddenException(PROJECT_ACCESS_FORBIDDEN_MESSAGE)

    async def _validate_task_creation(
        self,
        project_id: int,
        user: User,
        assignee_id: int | None,
    ) -> None:
        project = await self.reference_repository.get_project(project_id)

        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND_MESSAGE)

        membership = await self.workspace_repository.get_membership(
            workspace_id=project.workspace_id,
            user_id=user.id,
        )

        if not has_workspace_role(
            user,
            membership,
            {WorkspaceRole.OWNER, WorkspaceRole.EDITOR},
        ):
            raise ForbiddenException(PROJECT_ACCESS_FORBIDDEN_MESSAGE)

        if project.status == ProjectStatus.ARCHIVED:
            raise ForbiddenException(PROJECT_ACCESS_FORBIDDEN_MESSAGE)

        await self._validate_assignee(project.workspace_id, assignee_id)

    async def create_task(
        self,
        task_data: TaskCreate,
        user: User,
    ) -> Task:
        await self._validate_task_creation(
            project_id=task_data.project_id,
            user=user,
            assignee_id=task_data.assignee_id,
        )

        task = Task(
            **task_data.model_dump(),
            created_by=user.id,
        )

        await self._execute_write(lambda: self.repository.create(task))
        await self.session.refresh(task)

        return task

    async def get_all_tasks(
        self,
        user: User,
        limit: int,
        offset: int,
    ) -> tuple[list[Task], int]:
        return await self.repository.get_all(
            user_id=user.id,
            is_admin=user.role == UserRole.ADMIN,
            limit=limit,
            offset=offset,
        )

    async def get_task_by_id(
        self,
        task_id: int,
        user: User,
    ) -> Task:
        task = await self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

        await self._ensure_task_view_access(task, user)

        return task

    async def update_task(
        self,
        task_id: int,
        update_data: dict,
        user: User,
    ) -> Task:
        task = await self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

        await self._ensure_task_write_access(task, user)

        if "assignee_id" in update_data:
            project = await self.reference_repository.get_project(task.project_id)

            if project is None:
                raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

            await self._validate_assignee(
                workspace_id=project.workspace_id,
                assignee_id=update_data["assignee_id"],
            )

        await self._execute_write(lambda: self.repository.update(task, update_data))
        await self.session.refresh(task)

        return task

    async def delete_task(
        self,
        task_id: int,
        user: User,
    ) -> None:
        task = await self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

        await self._get_task_workspace_context(task, user)

        if user.role.value != "ADMIN":
            project = await self.reference_repository.get_project(task.project_id)
            membership = await self.workspace_repository.get_membership(
                workspace_id=project.workspace_id,
                user_id=user.id,
            )

            if membership is None:
                raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

            if membership.role == WorkspaceRole.EDITOR:
                if task.created_by != user.id:
                    raise ForbiddenException(PROJECT_ACCESS_FORBIDDEN_MESSAGE)
            elif membership.role != WorkspaceRole.OWNER:
                raise ForbiddenException(PROJECT_ACCESS_FORBIDDEN_MESSAGE)

        await self._execute_write(lambda: self.repository.delete(task))
