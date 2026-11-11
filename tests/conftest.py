from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.dependencies.common import get_db
from app.main import app
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace

TEST_DATABASE_NAME = "taskhub_test"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    database_url = URL.create(
        drivername="postgresql+asyncpg",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host="localhost",
        port=settings.POSTGRES_PORT,
        database=TEST_DATABASE_NAME,
    )

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()

            session_factory = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )

            async with session_factory() as session:
                yield session

            await transaction.rollback()

    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def async_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as test_client:
            yield test_client

    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def task_context(
    db_session: AsyncSession,
) -> dict[str, int]:
    user = User(
        email="task-test@example.com",
        full_name="Task Test User",
        hashed_password="test-hash",
    )

    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        name="Task Test Workspace",
        owner_id=user.id,
    )

    db_session.add(workspace)
    await db_session.flush()

    project = Project(
        workspace_id=workspace.id,
        name="Task Test Project",
    )

    db_session.add(project)
    await db_session.flush()

    return {
        "user_id": user.id,
        "workspace_id": workspace.id,
        "project_id": project.id,
    }
