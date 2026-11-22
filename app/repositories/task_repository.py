from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.flush()

        return task

    async def get_all_for_project(
        self,
        project_id: int,
        page: int,
        limit: int,
        statuses: list[TaskStatus] | None = None,
        priorities: list[TaskPriority] | None = None,
        assignee_id: int | None = None,
    ) -> tuple[list[Task], int]:
        filters = [Task.project_id == project_id]

        if statuses:
            filters.append(Task.status.in_(statuses))

        if priorities:
            filters.append(Task.priority.in_(priorities))

        if assignee_id is not None:
            filters.append(Task.assignee_id == assignee_id)

        total_statement = select(func.count()).select_from(Task).where(*filters)

        total = await self.session.scalar(total_statement)

        statement = (
            select(Task)
            .where(*filters)
            .order_by(Task.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )

        result = await self.session.scalars(statement)

        return list(result.all()), total or 0

    async def get_by_id(self, task_id: int) -> Task | None:
        return await self.session.get(Task, task_id)

    async def update(self, task: Task, update_data: dict) -> Task:
        for field, value in update_data.items():
            setattr(task, field, value)

        await self.session.flush()

        return task

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)
        await self.session.flush()
