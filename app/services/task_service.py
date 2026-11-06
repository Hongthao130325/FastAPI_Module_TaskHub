from app.core.exceptions import NotFoundException
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate


class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def create_task(self, task_data: TaskCreate) -> Task:
        task_data_dict = task_data.model_dump()

        return self.repository.create(task_data_dict)

    def get_all_tasks(self) -> list[Task]:
        return self.repository.get_all()

    def get_task_by_id(self, task_id: int) -> Task:
        task = self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException()

        return task

    def update_task(self, task_id: int, update_data: dict) -> Task:
        task = self.repository.update(task_id, update_data)

        if task is None:
            raise NotFoundException()

        return task

    def delete_task(self, task_id: int) -> None:
        deleted = self.repository.delete(task_id)

        if not deleted:
            raise NotFoundException()
