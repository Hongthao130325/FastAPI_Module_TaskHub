import os
import subprocess
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
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

_test_database_initialized = False


async def ensure_test_database() -> None:
    global _test_database_initialized

    if _test_database_initialized:
        return

    test_database_name = settings.POSTGRES_TEST_DB

    if test_database_name == settings.POSTGRES_DB:
        raise RuntimeError(
            "Test database must be different from the development database."
        )

    admin_database_url = settings.DATABASE_URL.set(database="postgres")

    admin_engine = create_async_engine(
        admin_database_url,
        isolation_level="AUTOCOMMIT",
    )

    try:
        async with admin_engine.connect() as connection:
            database_exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": test_database_name},
            )

            if not database_exists:
                quoted_database_name = connection.dialect.identifier_preparer.quote(
                    test_database_name
                )

                await connection.exec_driver_sql(
                    f"CREATE DATABASE {quoted_database_name}"
                )

    finally:
        await admin_engine.dispose()

    environment = os.environ.copy()
    environment["POSTGRES_DB"] = test_database_name

    project_root = Path(__file__).resolve().parents[1]

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root,
        env=environment,
        check=True,
    )

    _test_database_initialized = True


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    await ensure_test_database()

    test_database_url = settings.DATABASE_URL.set(database=settings.POSTGRES_TEST_DB)

    engine = create_async_engine(
        test_database_url,
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

            try:
                async with session_factory() as session:
                    yield session

            finally:
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
