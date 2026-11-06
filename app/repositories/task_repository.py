class TaskRepository:
    def __init__(self):
        self.tasks = {}
        self.next_id = 1

    def create(self, task_data: dict) -> dict:
        task = {
            "id": self.next_id,
            "title": task_data["title"],
            "description": task_data.get("description"),
            "is_completed": False
        }

        self.tasks[self.next_id] = task
        self.next_id += 1

        return task

    def get_all(self) -> list[dict]:
        return list(self.tasks.values())

    def get_by_id(self, task_id: int) -> dict | None:
        return self.tasks.get(task_id)

    def update(self, task_id: int, update_data: dict) -> dict | None:
        task = self.get_by_id(task_id)

        if task is None:
            return None

        task.update(update_data)

        return task

    def delete(self, task_id: int) -> bool:
        if task_id not in self.tasks:
            return False

        del self.tasks[task_id]

        return True