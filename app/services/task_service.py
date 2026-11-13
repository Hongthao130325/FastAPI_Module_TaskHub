from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.core.messages import (
    PROJECT_NOT_FOUND_MESSAGE,
    RESOURCE_CONFLICT_MESSAGE,
    TASK_NOT_FOUND_MESSAGE,
    USER_NOT_FOUND_MESSAGE,
)
from app.models.task import Task
from app.repositories.reference_repository import ReferenceRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate

T = TypeVar("T")


class TaskService:
    def __init__(
        self,
        session: AsyncSession,
        repository: TaskRepository,
        reference_repository: ReferenceRepository,
    ):
        self.session = session
        self.repository = repository
        self.reference_repository = reference_repository

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

    async def _validate_task_references(
        self,
        project_id: int,
        assignee_id: int | None,
    ) -> int:
        owner_id = await self.reference_repository.get_project_owner_id(project_id)

        if owner_id is None:
            raise NotFoundException(PROJECT_NOT_FOUND_MESSAGE)

        if assignee_id is not None:
            if not await self.reference_repository.user_exists(assignee_id):
                raise NotFoundException(USER_NOT_FOUND_MESSAGE)

        return owner_id

    async def create_task(self, task_data: TaskCreate) -> Task:
        created_by = await self._validate_task_references(
            project_id=task_data.project_id,
            assignee_id=task_data.assignee_id,
        )

        task = Task(
            **task_data.model_dump(),
            created_by=created_by,
        )

        await self._execute_write(lambda: self.repository.create(task))

        await self.session.refresh(task)

        return task

    async def get_all_tasks(
        self,
        limit: int,
        offset: int,
    ) -> tuple[list[Task], int]:
        return await self.repository.get_all(limit, offset)

    async def get_task_by_id(self, task_id: int) -> Task:
        task = await self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

        return task

    async def update_task(
        self,
        task_id: int,
        update_data: dict,
    ) -> Task:
        task = await self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

        if "assignee_id" in update_data and update_data["assignee_id"] is not None:
            if not await self.reference_repository.user_exists(
                update_data["assignee_id"]
            ):
                raise NotFoundException(USER_NOT_FOUND_MESSAGE)

        await self._execute_write(lambda: self.repository.update(task, update_data))

        await self.session.refresh(task)

        return task

    async def delete_task(self, task_id: int) -> None:
        task = await self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)

        await self._execute_write(lambda: self.repository.delete(task))
