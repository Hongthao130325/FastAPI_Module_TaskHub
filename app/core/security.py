from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import settings
from app.models.enums import TokenType

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("taskhub-dummy-password-for-timing-equalization")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        return password_hash.verify(plain_password, hashed_password)
    except (UnknownHashError, TypeError):
        return False


def _create_token(
    subject: str | int,
    session_id: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)

    payload = {
        "sub": str(subject),
        "sid": session_id,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type.value,
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )


def create_access_token(
    subject: str | int,
    session_id: str,
) -> str:
    return _create_token(
        subject=subject,
        session_id=session_id,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    subject: str | int,
    session_id: str,
) -> str:
    return _create_token(
        subject=subject,
        session_id=session_id,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def create_refresh_token_with_metadata(
    subject: str | int,
    session_id: str,
) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    jti = str(uuid4())
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expires_at = datetime.fromtimestamp(int(expires_at.timestamp()), UTC)

    payload = {
        "sub": str(subject),
        "sid": session_id,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
        "type": TokenType.REFRESH.value,
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )

    return token, jti, expires_at


def _decode_token(
    token: str,
    expected_type: TokenType,
) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=[settings.ALGORITHM],
        options={
            "require": [
                "sub",
                "sid",
                "jti",
                "iat",
                "exp",
                "type",
            ],
        },
    )

    if payload["type"] != expected_type.value:
        raise jwt.InvalidTokenError("Invalid token type.")

    if not isinstance(payload["sub"], str) or not payload["sub"].isdigit():
        raise jwt.InvalidTokenError("Invalid token subject.")

    for claim in ("sid", "jti"):
        if not isinstance(payload[claim], str) or not payload[claim]:
            raise jwt.InvalidTokenError(f"Invalid {claim} claim.")

    if not isinstance(payload["iat"], (int, float)):
        raise jwt.InvalidTokenError("Invalid issued-at claim.")

    if not isinstance(payload["exp"], (int, float)):
        raise jwt.InvalidTokenError("Invalid expiration claim.")

    return payload


def decode_access_token(token: str) -> dict[str, Any]:
    return _decode_token(token, TokenType.ACCESS)


def decode_refresh_token(token: str) -> dict[str, Any]:
    return _decode_token(token, TokenType.REFRESH)
