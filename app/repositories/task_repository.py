from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task
from app.models.workspace import Workspace


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.flush()

        return task

    async def get_all(
        self,
        user_id: int,
        limit: int,
        offset: int,
    ) -> tuple[list[Task], int]:
        count_statement = (
            select(func.count(Task.id))
            .join(Project, Task.project_id == Project.id)
            .join(Workspace, Project.workspace_id == Workspace.id)
            .where(Workspace.owner_id == user_id)
        )

        total = await self.session.scalar(count_statement)

        statement = (
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .join(Workspace, Project.workspace_id == Workspace.id)
            .where(Workspace.owner_id == user_id)
            .order_by(Task.id)
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.scalars(statement)

        return list(result.all()), total or 0

    async def get_by_id(self, task_id: int) -> Task | None:
        return await self.session.get(Task, task_id)

    async def update(
        self,
        task: Task,
        update_data: dict,
    ) -> Task:
        for field, value in update_data.items():
            setattr(task, field, value)

        await self.session.flush()

        return task

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)
