import hashlib
import json
import logging

from fastapi import BackgroundTasks
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
)
from app.core.messages import (
    TASK_ASSIGNEE_NOT_IN_WORKSPACE_MESSAGE,
    USER_NOT_FOUND_MESSAGE,
)
from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.user import User
from app.repositories.reference_repository import ReferenceRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.pagination import PaginationParams
from app.schemas.task import TaskCreate, TaskResponse
from app.services.background_tasks import send_task_assigned_email
from app.services.cache_service import CacheService
from app.services.task_authorization import TaskAuthorization
from app.services.transaction import execute_write

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(
        self,
        session: AsyncSession,
        repository: TaskRepository,
        reference_repository: ReferenceRepository,
        workspace_repository: WorkspaceRepository,
        authorization: TaskAuthorization,
        cache_service: CacheService,
    ):
        self.session = session
        self.repository = repository
        self.reference_repository = reference_repository
        self.workspace_repository = workspace_repository
        self.authorization = authorization
        self.cache_service = cache_service

    def _build_task_cache_key(
        self,
        project_id: int,
        pagination: PaginationParams,
        statuses: list[TaskStatus] | None,
        priorities: list[TaskPriority] | None,
        assignee_id: int | None,
    ) -> str:
        filters = {
            "statuses": sorted(item.value for item in statuses) if statuses else None,
            "priorities": sorted(item.value for item in priorities)
            if priorities
            else None,
            "assignee_id": assignee_id,
            "page": pagination.page,
            "limit": pagination.limit,
        }
        serialized_filters = json.dumps(filters, sort_keys=True)
        digest = hashlib.sha256(serialized_filters.encode()).hexdigest()

        return f"tasks:project:{project_id}:{digest}"

    async def _invalidate_project_cache(self, project_id: int) -> None:
        try:
            await self.cache_service.delete_pattern(f"tasks:project:{project_id}:*")
        except RedisError:
            logger.warning(
                "Failed to invalidate task cache for project %s",
                project_id,
                exc_info=True,
            )

    async def _validate_assignee(
        self,
        workspace_id: int,
        assignee_id: int | None,
    ) -> User | None:
        if assignee_id is None:
            return None

        assignee = await self.reference_repository.get_user(assignee_id)

        if assignee is None:
            raise NotFoundException(USER_NOT_FOUND_MESSAGE)

        membership = await self.workspace_repository.get_membership(
            workspace_id=workspace_id,
            user_id=assignee_id,
        )

        if membership is None:
            raise BadRequestException(TASK_ASSIGNEE_NOT_IN_WORKSPACE_MESSAGE)

        return assignee

    def _schedule_assignment_notification(
        self,
        background_tasks: BackgroundTasks,
        task: Task,
        assignee: User | None,
    ) -> None:
        if assignee is None:
            return

        background_tasks.add_task(
            send_task_assigned_email,
            to_email=assignee.email,
            recipient_name=assignee.full_name,
            task_title=task.title,
            task_id=task.id,
        )

    async def create_task(
        self,
        project_id: int,
        task_data: TaskCreate,
        user: User,
        background_tasks: BackgroundTasks,
    ) -> Task:
        context = await self.authorization.get_project_context(
            project_id,
            user,
        )
        self.authorization.ensure_write_access(context, user)

        assignee = await self._validate_assignee(
            context.project.workspace_id,
            task_data.assignee_id,
        )

        task = Task(
            **task_data.model_dump(),
            project_id=project_id,
            created_by=user.id,
        )

        await execute_write(self.session, lambda: self.repository.create(task))
        await self.session.refresh(task)
        await self._invalidate_project_cache(project_id)
        self._schedule_assignment_notification(
            background_tasks,
            task,
            assignee,
        )

        return task

    async def get_all_tasks(
        self,
        project_id: int,
        user: User,
        pagination: PaginationParams,
        statuses: list[TaskStatus] | None = None,
        priorities: list[TaskPriority] | None = None,
        assignee_id: int | None = None,
    ) -> tuple[list[TaskResponse], int]:
        await self.authorization.get_project_context(project_id, user)

        cache_key = self._build_task_cache_key(
            project_id,
            pagination,
            statuses,
            priorities,
            assignee_id,
        )

        try:
            cached_data = await self.cache_service.get(cache_key)

            if (
                isinstance(cached_data, dict)
                and isinstance(cached_data.get("items"), list)
                and isinstance(cached_data.get("total"), int)
            ):
                return [
                    TaskResponse.model_validate(item) for item in cached_data["items"]
                ], cached_data["total"]

        except (RedisError, ValueError, TypeError):
            logger.warning(
                "Failed to read task cache for project %s",
                project_id,
                exc_info=True,
            )

        tasks, total = await self.repository.get_all_for_project(
            project_id=project_id,
            pagination=pagination,
            statuses=statuses,
            priorities=priorities,
            assignee_id=assignee_id,
        )

        response_items = [TaskResponse.model_validate(task) for task in tasks]

        try:
            cached_items = [item.model_dump(mode="json") for item in response_items]
            await self.cache_service.set(
                cache_key,
                {"items": cached_items, "total": total},
            )
        except (RedisError, ValueError, TypeError):
            logger.warning(
                "Failed to write task cache for project %s",
                project_id,
                exc_info=True,
            )

        return response_items, total

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
        background_tasks: BackgroundTasks,
    ) -> Task:
        context = await self.authorization.get_task_context(task_id, user)
        self.authorization.ensure_write_access(context, user)

        previous_assignee_id = context.task.assignee_id
        assignee = None

        if "assignee_id" in update_data:
            assignee = await self._validate_assignee(
                workspace_id=context.project.workspace_id,
                assignee_id=update_data["assignee_id"],
            )

        await execute_write(
            self.session, lambda: self.repository.update(context.task, update_data)
        )
        await self.session.refresh(context.task)
        await self._invalidate_project_cache(context.project.id)

        if assignee is not None and assignee.id != previous_assignee_id:
            self._schedule_assignment_notification(
                background_tasks,
                context.task,
                assignee,
            )

        return context.task

    async def delete_task(
        self,
        task_id: int,
        user: User,
    ) -> None:
        context = await self.authorization.get_task_context(task_id, user)
        self.authorization.ensure_write_access(context, user)

        await execute_write(self.session, lambda: self.repository.delete(context.task))
        await self._invalidate_project_cache(context.project.id)
