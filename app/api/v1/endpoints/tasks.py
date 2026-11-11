from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import DEFAULT_OFFSET, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
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


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    task_data: TaskCreate,
    service: TaskServiceDep,
) -> TaskResponse:
    task = await service.create_task(task_data)

    return TaskResponse.model_validate(task)


@router.get("", response_model=TaskListResponse)
async def get_all_tasks(
    service: TaskServiceDep,
    limit: int = Query(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
    ),
    offset: int = Query(default=DEFAULT_OFFSET, ge=0),
) -> TaskListResponse:
    tasks, total = await service.get_all_tasks(limit, offset)

    return TaskListResponse(
        items=[TaskResponse.model_validate(task) for task in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    service: TaskServiceDep,
) -> TaskResponse:
    task = await service.get_task_by_id(task_id)

    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskServiceDep,
) -> TaskResponse:
    task = await service.update_task(
        task_id,
        task_data.model_dump(exclude_unset=True),
    )

    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: int,
    service: TaskServiceDep,
) -> None:
    await service.delete_task(task_id)
