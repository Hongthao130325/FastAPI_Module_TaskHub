from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.core.messages import (
    COMMENT_ACCESS_FORBIDDEN_MESSAGE,
    COMMENT_NOT_FOUND_MESSAGE,
    RESOURCE_CONFLICT_MESSAGE,
)
from app.core.permissions import has_workspace_role
from app.models.comment import Comment
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import CommentCreate, CommentUpdate
from app.schemas.pagination import PaginationParams
from app.services.task_authorization import TaskAuthorization

T = TypeVar("T")


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

    async def _execute_write(
        self,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        try:
            result = await operation()
            await self.session.commit()

            return result

        except IntegrityError as exc:
            await self.session.rollback()

            raise ConflictException(RESOURCE_CONFLICT_MESSAGE) from exc

        except Exception:
            await self.session.rollback()
            raise

    def _ensure_comment_modify_access(
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

        await self._execute_write(lambda: self.repository.create(comment))
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

        self._ensure_comment_modify_access(
            comment,
            context.membership,
            user,
        )

        data = update_data.model_dump(exclude_unset=True)

        await self._execute_write(lambda: self.repository.update(comment, data))
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

        self._ensure_comment_modify_access(
            comment,
            context.membership,
            user,
        )

        await self._execute_write(lambda: self.repository.delete(comment))
