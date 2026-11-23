from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
)
from app.core.messages import (
    COMMENT_ACCESS_FORBIDDEN_MESSAGE,
    COMMENT_NOT_FOUND_MESSAGE,
)
from app.core.permissions import has_workspace_role
from app.models.comment import Comment
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import CommentCreate, CommentUpdate
from app.schemas.pagination import PaginationParams
from app.services.task_authorization import TaskAuthorization
from app.services.transaction import execute_write


class CommentService:
    def __init__(
        self,
        session: AsyncSession,
        repository: CommentRepository,
        authorization: TaskAuthorization,
    ):
        self.session = session
        self.repository = repository
        self.authorization = authorization

    def _ensure_comment_update_access(
        self,
        comment: Comment,
        user: User,
    ) -> None:
        if comment.author_id != user.id:
            raise ForbiddenException(COMMENT_ACCESS_FORBIDDEN_MESSAGE)

    def _ensure_comment_delete_access(
        self,
        comment: Comment,
        membership,
        user: User,
    ) -> None:
        is_owner_or_admin = has_workspace_role(
            user,
            membership,
            {WorkspaceRole.OWNER},
        )

        if comment.author_id != user.id and not is_owner_or_admin:
            raise ForbiddenException(COMMENT_ACCESS_FORBIDDEN_MESSAGE)

    async def create_comment(
        self,
        task_id: int,
        comment_data: CommentCreate,
        user: User,
    ) -> Comment:
        context = await self.authorization.get_task_context(task_id, user)
        self.authorization.ensure_write_access(context, user)

        comment = Comment(
            task_id=task_id,
            author_id=user.id,
            content=comment_data.content,
        )

        await execute_write(self.session, lambda: self.repository.create(comment))
        await self.session.refresh(comment)

        return comment

    async def get_all_comments(
        self,
        task_id: int,
        user: User,
        pagination: PaginationParams,
    ) -> tuple[list[Comment], int]:
        await self.authorization.get_task_context(task_id, user)

        return await self.repository.get_all_for_task(
            task_id,
            pagination,
        )

    async def get_comment_by_id(
        self,
        task_id: int,
        comment_id: int,
        user: User,
    ) -> Comment:
        await self.authorization.get_task_context(task_id, user)

        comment = await self.repository.get_by_id(task_id, comment_id)

        if comment is None:
            raise NotFoundException(COMMENT_NOT_FOUND_MESSAGE)

        return comment

    async def update_comment(
        self,
        task_id: int,
        comment_id: int,
        update_data: CommentUpdate,
        user: User,
    ) -> Comment:
        context = await self.authorization.get_task_context(task_id, user)
        self.authorization.ensure_write_access(context, user)

        comment = await self.repository.get_by_id(task_id, comment_id)

        if comment is None:
            raise NotFoundException(COMMENT_NOT_FOUND_MESSAGE)

        self._ensure_comment_update_access(comment, user)

        data = update_data.model_dump(exclude_unset=True)

        await execute_write(self.session, lambda: self.repository.update(comment, data))
        await self.session.refresh(comment)

        return comment

    async def delete_comment(
        self,
        task_id: int,
        comment_id: int,
        user: User,
    ) -> None:
        context = await self.authorization.get_task_context(task_id, user)
        self.authorization.ensure_write_access(context, user)

        comment = await self.repository.get_by_id(task_id, comment_id)

        if comment is None:
            raise NotFoundException(COMMENT_NOT_FOUND_MESSAGE)

        self._ensure_comment_delete_access(
            comment,
            context.membership,
            user,
        )

        await execute_write(self.session, lambda: self.repository.delete(comment))
