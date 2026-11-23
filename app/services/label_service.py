from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.core.messages import (
    LABEL_ALREADY_ATTACHED_MESSAGE,
    LABEL_ALREADY_EXISTS_MESSAGE,
    LABEL_NOT_ATTACHED_MESSAGE,
    LABEL_NOT_FOUND_MESSAGE,
    LABEL_PROJECT_MISMATCH_MESSAGE,
    LABEL_UPDATE_EMPTY_MESSAGE,
)
from app.models.label import Label
from app.models.user import User
from app.repositories.label_repository import LabelRepository
from app.schemas.label import LabelCreate, LabelUpdate
from app.schemas.pagination import PaginationParams
from app.services.task_authorization import TaskAuthorization
from app.services.transaction import execute_write


class LabelService:
    def __init__(
        self,
        session: AsyncSession,
        repository: LabelRepository,
        authorization: TaskAuthorization,
    ):
        self.session = session
        self.repository = repository
        self.authorization = authorization

    async def create_label(
        self,
        project_id: int,
        label_data: LabelCreate,
        user: User,
    ) -> Label:
        context = await self.authorization.get_project_context(
            project_id,
            user,
        )
        self.authorization.ensure_write_access(context, user)

        label = Label(
            project_id=project_id,
            **label_data.model_dump(),
        )

        return await execute_write(
            self.session,
            lambda: self.repository.create(label),
            LABEL_ALREADY_EXISTS_MESSAGE,
        )

    async def get_all_labels(
        self,
        project_id: int,
        user: User,
        pagination: PaginationParams,
    ) -> tuple[list[Label], int]:
        await self.authorization.get_project_context(project_id, user)

        return await self.repository.get_all_for_project(
            project_id,
            pagination,
        )

    async def get_label_by_id(
        self,
        project_id: int,
        label_id: int,
        user: User,
    ) -> Label:
        await self.authorization.get_project_context(project_id, user)

        label = await self.repository.get_by_id(label_id)

        if label is None or label.project_id != project_id:
            raise NotFoundException(LABEL_NOT_FOUND_MESSAGE)

        return label

    async def update_label(
        self,
        project_id: int,
        label_id: int,
        update_data: LabelUpdate,
        user: User,
    ) -> Label:
        context = await self.authorization.get_project_context(
            project_id,
            user,
        )
        self.authorization.ensure_write_access(context, user)

        label = await self.repository.get_by_id(label_id)

        if label is None or label.project_id != project_id:
            raise NotFoundException(LABEL_NOT_FOUND_MESSAGE)

        data = update_data.model_dump(exclude_unset=True)

        if not data:
            raise BadRequestException(LABEL_UPDATE_EMPTY_MESSAGE)

        return await execute_write(
            self.session,
            lambda: self.repository.update(label, data),
            LABEL_ALREADY_EXISTS_MESSAGE,
        )

    async def delete_label(
        self,
        project_id: int,
        label_id: int,
        user: User,
    ) -> None:
        context = await self.authorization.get_project_context(
            project_id,
            user,
        )
        self.authorization.ensure_write_access(context, user)

        label = await self.repository.get_by_id(label_id)

        if label is None or label.project_id != project_id:
            raise NotFoundException(LABEL_NOT_FOUND_MESSAGE)

        await execute_write(
            self.session,
            lambda: self.repository.delete(label),
        )

    async def attach_label_to_task(
        self,
        task_id: int,
        label_id: int,
        user: User,
    ) -> None:
        context = await self.authorization.get_task_context(task_id, user)
        self.authorization.ensure_write_access(context, user)

        label = await self.repository.get_by_id(label_id)

        if label is None:
            raise NotFoundException(LABEL_NOT_FOUND_MESSAGE)

        if label.project_id != context.project.id:
            raise BadRequestException(LABEL_PROJECT_MISMATCH_MESSAGE)

        async def operation() -> None:
            attached = await self.repository.attach_to_task(
                task_id,
                label_id,
            )

            if not attached:
                raise ConflictException(LABEL_ALREADY_ATTACHED_MESSAGE)

        await execute_write(
            self.session,
            operation,
            LABEL_ALREADY_ATTACHED_MESSAGE,
        )

    async def detach_label_from_task(
        self,
        task_id: int,
        label_id: int,
        user: User,
    ) -> None:
        context = await self.authorization.get_task_context(task_id, user)
        self.authorization.ensure_write_access(context, user)

        label = await self.repository.get_by_id(label_id)

        if label is None:
            raise NotFoundException(LABEL_NOT_FOUND_MESSAGE)

        if label.project_id != context.project.id:
            raise BadRequestException(LABEL_PROJECT_MISMATCH_MESSAGE)

        async def operation() -> None:
            detached = await self.repository.detach_from_task(
                task_id,
                label_id,
            )

            if not detached:
                raise NotFoundException(LABEL_NOT_ATTACHED_MESSAGE)

        await execute_write(
            self.session,
            operation,
            LABEL_NOT_ATTACHED_MESSAGE,
        )
