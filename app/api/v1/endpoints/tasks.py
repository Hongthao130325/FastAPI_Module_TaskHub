from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, status

from app.core.constants import (
    DEFAULT_PAGE,
    DEFAULT_TASK_PAGE_SIZE,
    MAX_PAGE,
    MAX_PAGE_SIZE,
)
from app.dependencies.auth import CurrentUserDep
from app.dependencies.common import get_task_service
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.pagination import PaginationParams
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])
project_tasks_router = APIRouter(
    prefix="/projects/{project_id}/tasks",
    tags=["Tasks"],
)

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
ProjectId = Annotated[int, Path(gt=0)]
TaskId = Annotated[int, Path(gt=0)]

PageQuery = Annotated[int, Query(ge=1, le=MAX_PAGE)]
LimitQuery = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
StatusesQuery = Annotated[list[TaskStatus] | None, Query(alias="status")]
PrioritiesQuery = Annotated[list[TaskPriority] | None, Query(alias="priority")]
AssigneeQuery = Annotated[int | None, Query(gt=0)]


@project_tasks_router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task in a project",
    responses={
        401: {"description": "Invalid or expired access token."},
        403: {"description": "Insufficient workspace role."},
        404: {"description": "Project not found."},
        409: {"description": "Project is archived or resource conflict."},
        422: {"description": "Request validation error."},
    },
)
async def create_task(
    project_id: ProjectId,
    task_data: TaskCreate,
    service: TaskServiceDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    task = await service.create_task(
        project_id,
        task_data,
        current_user.user,
        background_tasks,
    )

    return TaskResponse.model_validate(task)


@project_tasks_router.get(
    "",
    response_model=TaskListResponse,
    summary="Get tasks in a project",
    responses={
        401: {"description": "Invalid or expired access token."},
        404: {"description": "Project not found."},
        422: {"description": "Request validation error."},
    },
)
async def get_all_tasks(
    project_id: ProjectId,
    service: TaskServiceDep,
    current_user: CurrentUserDep,
    page: PageQuery = DEFAULT_PAGE,
    limit: LimitQuery = DEFAULT_TASK_PAGE_SIZE,
    statuses: StatusesQuery = None,
    priorities: PrioritiesQuery = None,
    assignee_id: AssigneeQuery = None,
) -> TaskListResponse:
    tasks, total = await service.get_all_tasks(
        project_id=project_id,
        user=current_user.user,
        pagination=PaginationParams(page=page, limit=limit),
        statuses=statuses,
        priorities=priorities,
        assignee_id=assignee_id,
    )

    return TaskListResponse(
        items=tasks,
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task by ID",
    responses={
        401: {"description": "Invalid or expired access token."},
        404: {"description": "Task not found."},
        422: {"description": "Request validation error."},
    },
)
async def get_task_by_id(
    task_id: TaskId,
    service: TaskServiceDep,
    current_user: CurrentUserDep,
) -> TaskResponse:
    task = await service.get_task_by_id(task_id, current_user.user)

    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
    responses={
        401: {"description": "Invalid or expired access token."},
        403: {"description": "Insufficient workspace role."},
        404: {"description": "Task not found."},
        409: {"description": "Project is archived or resource conflict."},
        422: {"description": "Request validation error."},
    },
)
async def update_task(
    task_id: TaskId,
    task_data: TaskUpdate,
    service: TaskServiceDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    task = await service.update_task(
        task_id,
        task_data.model_dump(exclude_unset=True),
        current_user.user,
        background_tasks,
    )

    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    responses={
        401: {"description": "Invalid or expired access token."},
        403: {"description": "Insufficient workspace role."},
        404: {"description": "Task not found."},
        409: {"description": "Project is archived or resource conflict."},
        422: {"description": "Request validation error."},
    },
)
async def delete_task(
    task_id: TaskId,
    service: TaskServiceDep,
    current_user: CurrentUserDep,
) -> None:
    await service.delete_task(task_id, current_user.user)
