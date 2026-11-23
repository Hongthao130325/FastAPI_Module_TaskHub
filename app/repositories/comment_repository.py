from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.schemas.pagination import PaginationParams


class CommentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, comment: Comment) -> Comment:
        self.session.add(comment)
        await self.session.flush()

        return comment

    async def get_by_id(
        self,
        task_id: int,
        comment_id: int,
    ) -> Comment | None:
        statement = select(Comment).where(
            Comment.id == comment_id,
            Comment.task_id == task_id,
        )

        return await self.session.scalar(statement)

    async def get_all_for_task(
        self,
        task_id: int,
        pagination: PaginationParams,
    ) -> tuple[list[Comment], int]:
        filters = [Comment.task_id == task_id]

        total_statement = select(func.count()).select_from(Comment).where(*filters)
        total = await self.session.scalar(total_statement)

        statement = (
            select(Comment)
            .where(*filters)
            .order_by(Comment.created_at, Comment.id)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self.session.scalars(statement)

        return list(result.all()), total or 0

    async def update(
        self,
        comment: Comment,
        update_data: dict,
    ) -> Comment:
        for field, value in update_data.items():
            setattr(comment, field, value)

        await self.session.flush()

        return comment

    async def delete(self, comment: Comment) -> None:
        await self.session.delete(comment)
        await self.session.flush()
