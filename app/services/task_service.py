from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate


class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def create_task(self, task_data: TaskCreate) -> dict:
        task_data_dict = task_data.model_dump()

        return self.repository.create(task_data_dict)

    def get_all_tasks(self) -> list[dict]:
        return self.repository.get_all()

    def get_task_by_id(self, task_id: int) -> dict | None:
        return self.repository.get_by_id(task_id)

    def update_task(
        self,
        task_id: int,
        update_data: dict
    ) -> dict | None:
        return self.repository.update(task_id, update_data)

    def delete_task(self, task_id: int) -> bool:
        return self.repository.delete(task_id)

