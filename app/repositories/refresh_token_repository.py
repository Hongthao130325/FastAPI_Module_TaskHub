from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, refresh_token: RefreshToken) -> RefreshToken:
        self.session.add(refresh_token)
        await self.session.flush()

        return refresh_token

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        statement = (
            select(RefreshToken)
            .where(RefreshToken.jti == jti)
            .execution_options(populate_existing=True)
        )

        return await self.session.scalar(statement)

    async def consume(
        self,
        jti: str,
        user_id: int,
        session_id: str,
        replaced_by_jti: str,
    ) -> bool:
        now = datetime.now(UTC)

        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.jti == jti,
                RefreshToken.user_id == user_id,
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .values(
                revoked_at=now,
                replaced_by_jti=replaced_by_jti,
            )
            .returning(RefreshToken.jti)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none() is not None

    async def revoke_session(
        self,
        user_id: int,
        session_id: str,
    ) -> None:
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

        await self.session.execute(statement)

    async def revoke_all_for_user(self, user_id: int) -> None:
        now = datetime.now(UTC)

        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

        await self.session.execute(statement)

    async def has_active_session(
        self,
        user_id: int,
        session_id: str,
    ) -> bool:
        statement = (
            select(RefreshToken.jti)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
            .limit(1)
        )

        result = await self.session.scalar(statement)

        return result is not None
