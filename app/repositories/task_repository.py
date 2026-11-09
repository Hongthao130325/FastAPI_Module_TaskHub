from app.core.constants import DEFAULT_TASK_IS_COMPLETED
from app.models.task import Task


class TaskRepository:
    def __init__(self):
        self.tasks: dict[int, Task] = {}
        self.next_id = 1

    def create(self, task_data: dict) -> Task:
        task = Task(
            id=self.next_id,
            title=task_data["title"],
            description=task_data.get("description"),
            is_completed=DEFAULT_TASK_IS_COMPLETED,
        )

        self.tasks[self.next_id] = task
        self.next_id += 1

        return task

    def get_all(self) -> list[Task]:
        return list(self.tasks.values())

    def get_by_id(self, task_id: int) -> Task | None:
        return self.tasks.get(task_id)

    def update(self, task_id: int, update_data: dict) -> Task | None:
        task = self.get_by_id(task_id)

        if task is None:
            return None

        for field, value in update_data.items():
            setattr(task, field, value)

        return task

    def delete(self, task_id: int) -> bool:
        if task_id not in self.tasks:
            return False

        del self.tasks[task_id]

        return True
