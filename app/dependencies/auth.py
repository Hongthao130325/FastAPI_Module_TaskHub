from typing import Annotated, NamedTuple

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.messages import (
    INACTIVE_USER_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
)
from app.core.security import decode_access_token
from app.dependencies.common import get_db
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(NamedTuple):
    user: User
    session_id: str


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthenticatedUser:
    if credentials is None:
        raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE) from exc

    repository = UserRepository(session)
    user = await repository.get_by_id(int(payload["sub"]))

    if user is None:
        raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

    if not user.is_active:
        raise UnauthorizedException(INACTIVE_USER_MESSAGE)

    refresh_token_repository = RefreshTokenRepository(session)
    has_active_session = await refresh_token_repository.has_active_session(
        user_id=user.id,
        session_id=payload["sid"],
    )

    if not has_active_session:
        raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

    return AuthenticatedUser(
        user=user,
        session_id=payload["sid"],
    )


CurrentUserDep = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]
