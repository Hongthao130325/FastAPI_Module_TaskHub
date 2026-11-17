from datetime import UTC, datetime
from uuid import uuid4

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    UnauthorizedException,
)
from app.core.messages import (
    EMAIL_ALREADY_REGISTERED_MESSAGE,
    INACTIVE_USER_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    INVALID_CURRENT_PASSWORD_MESSAGE,
    NEW_PASSWORD_SAME_AS_CURRENT_MESSAGE,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    ChangePassword,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ):
        self.session = session
        self.repository = repository
        self.refresh_token_repository = refresh_token_repository

    async def register(self, user_data: UserRegister) -> User:
        user = User(
            email=str(user_data.email).lower(),
            full_name=user_data.full_name,
            hashed_password=hash_password(user_data.password),
            role=UserRole.MEMBER,
        )

        try:
            async with self.session.begin_nested():
                await self.repository.create(user)

            await self.session.commit()

        except IntegrityError as exc:
            raise ConflictException(EMAIL_ALREADY_REGISTERED_MESSAGE) from exc

        await self.session.refresh(user)

        return user

    async def login(self, login_data: UserLogin) -> TokenResponse:
        user = await self.repository.get_by_email(str(login_data.email).lower())

        if user is None or not verify_password(
            login_data.password,
            user.hashed_password,
        ):
            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

        if not user.is_active:
            raise ForbiddenException(INACTIVE_USER_MESSAGE)

        session_id = str(uuid4())

        access_token = create_access_token(user.id, session_id)
        refresh_token = create_refresh_token(user.id, session_id)

        payload = decode_refresh_token(refresh_token)

        refresh_token_record = RefreshToken(
            jti=payload["jti"],
            user_id=user.id,
            session_id=session_id,
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )

        await self.refresh_token_repository.create(refresh_token_record)
        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh(
        self,
        refresh_data: RefreshRequest,
    ) -> TokenResponse:
        try:
            payload = decode_refresh_token(refresh_data.refresh_token)
        except jwt.InvalidTokenError as exc:
            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE) from exc

        token_record = await self.refresh_token_repository.get_by_jti(
            payload["jti"],
        )

        if token_record is None:
            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

        if (
            token_record.user_id != int(payload["sub"])
            or token_record.session_id != payload["sid"]
        ):
            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

        if token_record.revoked_at is not None:
            await self.refresh_token_repository.revoke_session(
                user_id=token_record.user_id,
                session_id=token_record.session_id,
            )
            await self.session.commit()

            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

        if token_record.expires_at <= datetime.now(UTC):
            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

        user = await self.repository.get_by_id(token_record.user_id)

        if user is None:
            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

        if not user.is_active:
            await self.refresh_token_repository.revoke_all_for_user(user.id)
            await self.session.commit()

            raise ForbiddenException(INACTIVE_USER_MESSAGE)

        new_access_token = create_access_token(user.id, token_record.session_id)
        new_refresh_token = create_refresh_token(user.id, token_record.session_id)

        new_payload = decode_refresh_token(new_refresh_token)

        new_token_record = RefreshToken(
            jti=new_payload["jti"],
            user_id=user.id,
            session_id=token_record.session_id,
            expires_at=datetime.fromtimestamp(new_payload["exp"], UTC),
        )

        consumed = await self.refresh_token_repository.consume(
            jti=token_record.jti,
            user_id=user.id,
            session_id=token_record.session_id,
            replaced_by_jti=new_payload["jti"],
        )

        if not consumed:
            current_record = await self.refresh_token_repository.get_by_jti(
                token_record.jti,
            )

            if current_record is not None and current_record.revoked_at is not None:
                await self.refresh_token_repository.revoke_session(
                    user_id=user.id,
                    session_id=token_record.session_id,
                )
                await self.session.commit()
            else:
                await self.session.rollback()

            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

        await self.refresh_token_repository.create(new_token_record)
        await self.session.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

    async def change_password(
        self,
        user_id: int,
        password_data: ChangePassword,
    ) -> None:
        user = await self.repository.get_by_id(user_id)

        if user is None:
            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

        if not verify_password(
            password_data.current_password,
            user.hashed_password,
        ):
            raise UnauthorizedException(INVALID_CURRENT_PASSWORD_MESSAGE)

        if password_data.current_password == password_data.new_password:
            raise BadRequestException(NEW_PASSWORD_SAME_AS_CURRENT_MESSAGE)

        user.hashed_password = hash_password(password_data.new_password)

        await self.refresh_token_repository.revoke_all_for_user(user_id)
        await self.session.commit()

    async def logout(
        self,
        user_id: int,
        session_id: str,
    ) -> None:
        await self.refresh_token_repository.revoke_session(
            user_id=user_id,
            session_id=session_id,
        )

        await self.session.commit()
