from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.common import get_task_service
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
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
    return service.create_task(task_data)


@router.get("", response_model=list[TaskResponse])
async def get_all_tasks(
    service: TaskServiceDep,
) -> list[TaskResponse]:
    return service.get_all_tasks()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    service: TaskServiceDep,
) -> TaskResponse:
    return service.get_task_by_id(task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskServiceDep,
) -> TaskResponse:
    return service.update_task(
        task_id,
        task_data.model_dump(exclude_unset=True),
    )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: int,
    service: TaskServiceDep,
) -> None:
    service.delete_task(task_id)
