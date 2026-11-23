from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label
from app.models.task_label import TaskLabel
from app.schemas.pagination import PaginationParams


class LabelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, label: Label) -> Label:
        self.session.add(label)
        await self.session.flush()

        return label

    async def get_by_id(self, label_id: int) -> Label | None:
        return await self.session.get(Label, label_id)

    async def get_all_for_project(
        self,
        project_id: int,
        pagination: PaginationParams,
    ) -> tuple[list[Label], int]:
        filters = [Label.project_id == project_id]

        total_statement = select(func.count()).select_from(Label).where(*filters)
        total = await self.session.scalar(total_statement)

        statement = (
            select(Label)
            .where(*filters)
            .order_by(Label.id)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self.session.scalars(statement)

        return list(result.all()), total or 0

    async def update(
        self,
        label: Label,
        update_data: dict,
    ) -> Label:
        for field, value in update_data.items():
            setattr(label, field, value)

        await self.session.flush()

        return label

    async def delete(self, label: Label) -> None:
        await self.session.delete(label)
        await self.session.flush()

    async def attach_to_task(
        self,
        task_id: int,
        label_id: int,
    ) -> bool:
        statement = (
            insert(TaskLabel)
            .values(task_id=task_id, label_id=label_id)
            .on_conflict_do_nothing(
                index_elements=[
                    TaskLabel.task_id,
                    TaskLabel.label_id,
                ],
            )
            .returning(TaskLabel.task_id)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none() is not None

    async def detach_from_task(
        self,
        task_id: int,
        label_id: int,
    ) -> bool:
        statement = (
            delete(TaskLabel)
            .where(
                TaskLabel.task_id == task_id,
                TaskLabel.label_id == label_id,
            )
            .returning(TaskLabel.task_id)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none() is not None
