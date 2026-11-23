from dataclasses import dataclass

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.messages import (
    WORKSPACE_ACCESS_FORBIDDEN_MESSAGE,
    WORKSPACE_NOT_FOUND_MESSAGE,
)
from app.core.permissions import has_workspace_role
from app.models.enums import UserRole, WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.workspace_repository import WorkspaceRepository


@dataclass
class WorkspaceAccessContext:
    workspace: Workspace
    membership: WorkspaceMember | None


class WorkspaceAuthorization:
    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    async def get_workspace_context(
        self,
        workspace_id: int,
        user: User,
        for_update: bool = False,
    ) -> WorkspaceAccessContext:
        if for_update:
            workspace = await self.repository.get_by_id_for_update(workspace_id)
        else:
            workspace = await self.repository.get_by_id(workspace_id)

        if workspace is None:
            raise NotFoundException(WORKSPACE_NOT_FOUND_MESSAGE)

        membership = await self.repository.get_membership(
            workspace_id,
            user.id,
        )

        if membership is None and user.role != UserRole.ADMIN:
            raise NotFoundException(WORKSPACE_NOT_FOUND_MESSAGE)

        return WorkspaceAccessContext(
            workspace=workspace,
            membership=membership,
        )

    @staticmethod
    def ensure_role_access(
        context: WorkspaceAccessContext,
        user: User,
        allowed_roles: set[WorkspaceRole],
    ) -> None:
        if not has_workspace_role(user, context.membership, allowed_roles):
            raise ForbiddenException(WORKSPACE_ACCESS_FORBIDDEN_MESSAGE)
