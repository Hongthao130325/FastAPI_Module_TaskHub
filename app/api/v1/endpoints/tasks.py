from fastapi import APIRouter, Depends

from app.core.constants import TASK_DELETED_MESSAGE
from app.dependencies.common import get_task_service
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate, service: TaskService = Depends(get_task_service)
):
    return service.create_task(task_data)


@router.get("/", response_model=list[TaskResponse])
async def get_all_tasks(service: TaskService = Depends(get_task_service)):
    return service.get_all_tasks()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int, service: TaskService = Depends(get_task_service)
):
    return service.get_task_by_id(task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
):
    return service.update_task(task_id, task_data.model_dump(exclude_unset=True))


@router.delete("/{task_id}")
async def delete_task(task_id: int, service: TaskService = Depends(get_task_service)):
    service.delete_task(task_id)

    return {"message": TASK_DELETED_MESSAGE}
