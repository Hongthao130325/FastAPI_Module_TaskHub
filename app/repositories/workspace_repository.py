from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, workspace: Workspace) -> Workspace:
        self.session.add(workspace)
        await self.session.flush()

        return workspace

    async def get_by_id(self, workspace_id: int) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

    async def get_by_id_for_update(
        self,
        workspace_id: int,
    ) -> Workspace | None:
        statement = (
            select(Workspace).where(Workspace.id == workspace_id).with_for_update()
        )

        return await self.session.scalar(statement)

    async def get_all(
        self,
        limit: int,
        offset: int,
    ) -> tuple[list[Workspace], int]:
        count_statement = select(func.count(Workspace.id))
        total = await self.session.scalar(count_statement)

        statement = select(Workspace).order_by(Workspace.id).limit(limit).offset(offset)
        result = await self.session.scalars(statement)

        return list(result.all()), total or 0

    async def get_all_for_user(
        self,
        user_id: int,
        limit: int,
        offset: int,
    ) -> tuple[list[Workspace], int]:
        count_statement = (
            select(func.count(Workspace.id))
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(WorkspaceMember.user_id == user_id)
        )
        total = await self.session.scalar(count_statement)

        statement = (
            select(Workspace)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(statement)

        return list(result.all()), total or 0

    async def get_membership(
        self,
        workspace_id: int,
        user_id: int,
    ) -> WorkspaceMember | None:
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )

        return await self.session.scalar(statement)

    async def get_members(
        self,
        workspace_id: int,
    ) -> list[tuple[WorkspaceMember, User]]:
        statement = (
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.user_id)
        )

        result = await self.session.execute(statement)

        return list(result.all())

    async def add_member(
        self,
        membership: WorkspaceMember,
    ) -> WorkspaceMember:
        self.session.add(membership)
        await self.session.flush()

        return membership

    async def update(
        self,
        workspace: Workspace,
        update_data: dict,
    ) -> Workspace:
        for field, value in update_data.items():
            setattr(workspace, field, value)

        await self.session.flush()

        return workspace

    async def delete(self, workspace: Workspace) -> None:
        await self.session.delete(workspace)
        await self.session.flush()

    async def remove_member(self, membership: WorkspaceMember) -> None:
        await self.session.delete(membership)
        await self.session.flush()

    async def update_member_role(
        self,
        membership: WorkspaceMember,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        membership.role = role
        await self.session.flush()

        return membership
