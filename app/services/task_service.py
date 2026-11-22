from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.core.messages import (
    RESOURCE_CONFLICT_MESSAGE,
    TASK_ASSIGNEE_NOT_IN_WORKSPACE_MESSAGE,
    USER_NOT_FOUND_MESSAGE,
)
from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.user import User
from app.repositories.reference_repository import ReferenceRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.task import TaskCreate
from app.services.task_authorization import (
    TaskAuthorization,
)

T = TypeVar("T")


class TaskService:
    def __init__(
        self,
        session: AsyncSession,
        repository: TaskRepository,
        reference_repository: ReferenceRepository,
        workspace_repository: WorkspaceRepository,
        authorization: TaskAuthorization,
    ):
        self.session = session
        self.repository = repository
        self.reference_repository = reference_repository
        self.workspace_repository = workspace_repository
        self.authorization = authorization

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
            raise BadRequestException(TASK_ASSIGNEE_NOT_IN_WORKSPACE_MESSAGE)

    async def create_task(
        self,
        project_id: int,
        task_data: TaskCreate,
        user: User,
    ) -> Task:
        context = await self.authorization.get_project_context(
            project_id,
            user,
        )
        self.authorization.ensure_write_access(context, user)

        await self._validate_assignee(
            context.project.workspace_id,
            task_data.assignee_id,
        )

        task = Task(
            **task_data.model_dump(),
            project_id=project_id,
            created_by=user.id,
        )

        await self._execute_write(lambda: self.repository.create(task))
        await self.session.refresh(task)

        return task

    async def get_all_tasks(
        self,
        project_id: int,
        user: User,
        page: int,
        limit: int,
        statuses: list[TaskStatus] | None = None,
        priorities: list[TaskPriority] | None = None,
        assignee_id: int | None = None,
    ) -> tuple[list[Task], int]:
        await self.authorization.get_project_context(project_id, user)

        return await self.repository.get_all_for_project(
            project_id=project_id,
            page=page,
            limit=limit,
            statuses=statuses,
            priorities=priorities,
            assignee_id=assignee_id,
        )

    async def get_task_by_id(
        self,
        task_id: int,
        user: User,
    ) -> Task:
        context = await self.authorization.get_task_context(task_id, user)

        return context.task

    async def update_task(
        self,
        task_id: int,
        update_data: dict,
        user: User,
    ) -> Task:
        context = await self.authorization.get_task_context(task_id, user)
        self.authorization.ensure_write_access(context, user)

        if "assignee_id" in update_data:
            await self._validate_assignee(
                workspace_id=context.project.workspace_id,
                assignee_id=update_data["assignee_id"],
            )

        await self._execute_write(
            lambda: self.repository.update(context.task, update_data)
        )
        await self.session.refresh(context.task)

        return context.task

    async def delete_task(
        self,
        task_id: int,
        user: User,
    ) -> None:
        context = await self.authorization.get_task_context(task_id, user)
        self.authorization.ensure_write_access(context, user)

        await self._execute_write(lambda: self.repository.delete(context.task))
