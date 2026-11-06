from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService


task_repository = TaskRepository()


def get_task_service() -> TaskService:
    return TaskService(task_repository)