from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.core.messages import (
    WORKSPACE_INVITATION_USER_NOT_FOUND_MESSAGE,
    WORKSPACE_MEMBER_ALREADY_EXISTS_MESSAGE,
    WORKSPACE_MEMBER_NOT_FOUND_MESSAGE,
    WORKSPACE_NOT_FOUND_MESSAGE,
    WORKSPACE_OWNER_CANNOT_BE_REMOVED_MESSAGE,
    WORKSPACE_OWNER_REQUIRED_MESSAGE,
    WORKSPACE_OWNER_ROLE_CANNOT_BE_CHANGED_MESSAGE,
    WORKSPACE_UPDATE_EMPTY_MESSAGE,
)
from app.models.enums import UserRole, WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.transaction import execute_write
from app.services.workspace_authorization import WorkspaceAuthorization


class WorkspaceService:
    def __init__(
        self,
        session: AsyncSession,
        repository: WorkspaceRepository,
        user_repository: UserRepository,
        authorization: WorkspaceAuthorization,
    ):
        self.session = session
        self.repository = repository
        self.user_repository = user_repository
        self.authorization = authorization

    async def _get_workspace(self, workspace_id: int) -> Workspace:
        workspace = await self.repository.get_by_id(workspace_id)

        if workspace is None:
            raise NotFoundException(WORKSPACE_NOT_FOUND_MESSAGE)

        return workspace

    async def _ensure_workspace_access(
        self,
        workspace_id: int,
        user: User,
        allowed_roles: set[WorkspaceRole],
    ) -> Workspace:
        context = await self.authorization.get_workspace_context(
            workspace_id,
            user,
        )
        self.authorization.ensure_role_access(context, user, allowed_roles)

        return context.workspace

    async def _ensure_workspace_owner(
        self,
        workspace_id: int,
        user: User,
    ) -> Workspace:
        workspace = await self._ensure_workspace_access(
            workspace_id,
            user,
            {WorkspaceRole.OWNER},
        )

        if user.role != UserRole.ADMIN and workspace.owner_id != user.id:
            raise ForbiddenException(WORKSPACE_OWNER_REQUIRED_MESSAGE)

        return workspace

    async def _ensure_workspace_owner_for_update(
        self,
        workspace_id: int,
        user: User,
    ) -> Workspace:
        context = await self.authorization.get_workspace_context(
            workspace_id,
            user,
            for_update=True,
        )
        self.authorization.ensure_role_access(
            context,
            user,
            {WorkspaceRole.OWNER},
        )

        workspace = context.workspace

        if user.role != UserRole.ADMIN and workspace.owner_id != user.id:
            raise ForbiddenException(WORKSPACE_OWNER_REQUIRED_MESSAGE)

        return workspace

    async def create_workspace(
        self,
        name: str,
        user: User,
    ) -> Workspace:
        workspace = Workspace(
            name=name,
            owner_id=user.id,
        )

        async def operation() -> Workspace:
            await self.repository.create(workspace)

            membership = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.OWNER,
            )

            await self.repository.add_member(membership)

            return workspace

        await execute_write(self.session, operation)
        await self.session.refresh(workspace)

        return workspace

    async def get_all_workspaces(
        self,
        user: User,
        limit: int,
        offset: int,
    ) -> tuple[list[Workspace], int]:
        if user.role == UserRole.ADMIN:
            return await self.repository.get_all(limit, offset)

        return await self.repository.get_all_for_user(
            user.id,
            limit,
            offset,
        )

    async def get_workspace_by_id(
        self,
        workspace_id: int,
        user: User,
    ) -> Workspace:
        return await self._ensure_workspace_access(
            workspace_id,
            user,
            {
                WorkspaceRole.OWNER,
                WorkspaceRole.EDITOR,
                WorkspaceRole.VIEWER,
            },
        )

    async def update_workspace(
        self,
        workspace_id: int,
        update_data: dict,
        user: User,
    ) -> Workspace:
        workspace = await self._ensure_workspace_owner(workspace_id, user)

        if not update_data:
            raise BadRequestException(WORKSPACE_UPDATE_EMPTY_MESSAGE)

        await execute_write(
            self.session, lambda: self.repository.update(workspace, update_data)
        )
        await self.session.refresh(workspace)

        return workspace

    async def delete_workspace(
        self,
        workspace_id: int,
        user: User,
    ) -> None:
        workspace = await self._ensure_workspace_owner(workspace_id, user)

        await execute_write(self.session, lambda: self.repository.delete(workspace))

    async def get_workspace_members(
        self,
        workspace_id: int,
        user: User,
    ) -> list[tuple[WorkspaceMember, User]]:
        await self._ensure_workspace_access(
            workspace_id,
            user,
            {
                WorkspaceRole.OWNER,
                WorkspaceRole.EDITOR,
                WorkspaceRole.VIEWER,
            },
        )

        return await self.repository.get_members(workspace_id)

    async def add_workspace_member(
        self,
        workspace_id: int,
        email: str,
        role: WorkspaceRole,
        current_user: User,
    ) -> tuple[WorkspaceMember, User]:
        await self._ensure_workspace_owner_for_update(
            workspace_id,
            current_user,
        )

        member_user = await self.user_repository.get_by_email(email.lower())

        if member_user is None:
            raise NotFoundException(WORKSPACE_INVITATION_USER_NOT_FOUND_MESSAGE)

        existing_membership = await self.repository.get_membership(
            workspace_id,
            member_user.id,
        )

        if existing_membership is not None:
            raise ConflictException(WORKSPACE_MEMBER_ALREADY_EXISTS_MESSAGE)

        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=member_user.id,
            role=role,
        )

        await execute_write(
            self.session, lambda: self.repository.add_member(membership)
        )

        return membership, member_user

    async def remove_workspace_member(
        self,
        workspace_id: int,
        user_id: int,
        current_user: User,
    ) -> None:
        workspace = await self._ensure_workspace_owner_for_update(
            workspace_id,
            current_user,
        )

        if user_id == workspace.owner_id:
            raise BadRequestException(WORKSPACE_OWNER_CANNOT_BE_REMOVED_MESSAGE)

        membership = await self.repository.get_membership(
            workspace_id,
            user_id,
        )

        if membership is None:
            raise NotFoundException(WORKSPACE_MEMBER_NOT_FOUND_MESSAGE)

        await execute_write(
            self.session, lambda: self.repository.remove_member(membership)
        )

    async def update_workspace_member_role(
        self,
        workspace_id: int,
        user_id: int,
        role: WorkspaceRole,
        current_user: User,
    ) -> tuple[WorkspaceMember, User]:
        workspace = await self._ensure_workspace_owner_for_update(
            workspace_id,
            current_user,
        )

        if user_id == workspace.owner_id:
            raise BadRequestException(WORKSPACE_OWNER_ROLE_CANNOT_BE_CHANGED_MESSAGE)

        membership = await self.repository.get_membership(
            workspace_id,
            user_id,
        )

        if membership is None:
            raise NotFoundException(WORKSPACE_MEMBER_NOT_FOUND_MESSAGE)

        await execute_write(
            self.session, lambda: self.repository.update_member_role(membership, role)
        )

        member_user = await self.user_repository.get_by_id(user_id)

        if member_user is None:
            raise NotFoundException(WORKSPACE_MEMBER_NOT_FOUND_MESSAGE)

        return membership, member_user
