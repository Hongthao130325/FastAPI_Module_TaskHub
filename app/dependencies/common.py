from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.repositories.reference_repository import ReferenceRepository
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_task_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskService:
    task_repository = TaskRepository(session)
    reference_repository = ReferenceRepository(session)

    return TaskService(
        repository=task_repository,
        reference_repository=reference_repository,
    )
