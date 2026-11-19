from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import DEFAULT_OFFSET, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.dependencies.auth import CurrentUserDep
from app.dependencies.common import get_task_service
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
LimitQuery = Annotated[
    int,
    Query(
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Maximum number of tasks to return.",
    ),
]
OffsetQuery = Annotated[
    int,
    Query(
        ge=0,
        description="Number of tasks to skip.",
    ),
]


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    responses={
        401: {"description": "Invalid or expired access token."},
        403: {"description": "No permission to create a task in this project."},
        404: {"description": "Referenced project or workspace does not exist."},
        422: {"description": "Request validation error."},
    },
)
async def create_task(
    task_data: TaskCreate,
    service: TaskServiceDep,
    current_user: CurrentUserDep,
) -> TaskResponse:
    task = await service.create_task(
        task_data,
        current_user.user.id,
    )

    return TaskResponse.model_validate(task)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="Get all tasks",
    responses={
        200: {"description": "Tasks retrieved successfully."},
        401: {"description": "Invalid or expired access token."},
        403: {"description": "User account is inactive."},
        422: {"description": "Invalid pagination parameters."},
    },
)
async def get_all_tasks(
    service: TaskServiceDep,
    current_user: CurrentUserDep,
    limit: LimitQuery = DEFAULT_PAGE_SIZE,
    offset: OffsetQuery = DEFAULT_OFFSET,
) -> TaskListResponse:
    tasks, total = await service.get_all_tasks(
        user_id=current_user.user.id,
        limit=limit,
        offset=offset,
    )

    return TaskListResponse(
        items=[TaskResponse.model_validate(task) for task in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task by ID",
    responses={
        401: {"description": "Invalid or expired access token."},
        403: {"description": "User account is inactive."},
        404: {"description": "Task not found."},
        422: {"description": "Invalid task ID."},
    },
)
async def get_task_by_id(
    task_id: int,
    service: TaskServiceDep,
    current_user: CurrentUserDep,
) -> TaskResponse:
    task = await service.get_task_by_id(
        task_id,
        current_user.user.id,
    )

    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
    responses={
        401: {"description": "Invalid or expired access token."},
        403: {"description": "User account is inactive."},
        404: {"description": "Task not found."},
        422: {"description": "Request validation error."},
    },
)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskServiceDep,
    current_user: CurrentUserDep,
) -> TaskResponse:
    task = await service.update_task(
        task_id,
        task_data.model_dump(exclude_unset=True),
        current_user.user.id,
    )

    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    responses={
        401: {"description": "Invalid or expired access token."},
        403: {"description": "User account is inactive."},
        404: {"description": "Task not found."},
        422: {"description": "Invalid task ID."},
    },
)
async def delete_task(
    task_id: int,
    service: TaskServiceDep,
    current_user: CurrentUserDep,
) -> None:
    await service.delete_task(
        task_id,
        current_user.user.id,
    )
