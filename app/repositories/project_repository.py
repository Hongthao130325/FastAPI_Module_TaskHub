from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project: Project) -> Project:
        self.session.add(project)
        await self.session.flush()

        return project

    async def get_by_id(self, project_id: int) -> Project | None:
        return await self.session.get(Project, project_id)

    async def get_all(self) -> list[Project]:
        statement = select(Project).order_by(Project.id)

        return list(await self.session.scalars(statement))

    async def get_all_for_workspace(
        self,
        workspace_id: int,
    ) -> list[Project]:
        statement = (
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.id)
        )

        return list(await self.session.scalars(statement))

    async def get_all_for_user(
        self,
        user_id: int,
    ) -> list[Project]:
        statement = (
            select(Project)
            .join(Workspace, Workspace.id == Project.workspace_id)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Project.id)
        )

        return list(await self.session.scalars(statement))

    async def update(
        self,
        project: Project,
        update_data: dict,
    ) -> Project:
        for field, value in update_data.items():
            setattr(project, field, value)

        await self.session.flush()

        return project

    async def archive(self, project: Project) -> Project:
        project.status = ProjectStatus.ARCHIVED
        await self.session.flush()

        return project
