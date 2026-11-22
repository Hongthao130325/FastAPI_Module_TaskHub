from app.models.enums import UserRole, WorkspaceRole
from app.models.user import User
from app.models.workspace_member import WorkspaceMember


def has_workspace_role(
    user: User,
    membership: WorkspaceMember | None,
    allowed_roles: set[WorkspaceRole],
) -> bool:
    if user.role == UserRole.ADMIN:
        return True

    return membership is not None and membership.role in allowed_roles
