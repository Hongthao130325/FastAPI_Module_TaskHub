from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.user import User


class ReferenceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def project_exists(self, project_id: int) -> bool:
        project = await self.session.get(Project, project_id)

        return project is not None

    async def user_exists(self, user_id: int) -> bool:
        user = await self.session.get(User, user_id)

        return user is not None
