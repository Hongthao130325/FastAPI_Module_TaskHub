from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()

        return user

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)

        return await self.session.scalar(statement)

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)
