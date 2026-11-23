from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException
from app.core.messages import RESOURCE_CONFLICT_MESSAGE

T = TypeVar("T")


async def execute_write(
    session: AsyncSession,
    operation: Callable[[], Awaitable[T]],
    conflict_message: str = RESOURCE_CONFLICT_MESSAGE,
) -> T:
    try:
        result = await operation()
        await session.commit()

        return result

    except IntegrityError as exc:
        await session.rollback()

        raise ConflictException(conflict_message) from exc

    except Exception:
        await session.rollback()
        raise
