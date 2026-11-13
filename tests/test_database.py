from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_database_connection(db_session: AsyncSession):
    result = await db_session.execute(text("SELECT current_database()"))

    database_name = result.scalar_one()

    assert database_name == "taskhub_test"
