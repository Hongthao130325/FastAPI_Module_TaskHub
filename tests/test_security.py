from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


def test_hash_password_returns_hash() -> None:
    hashed_password = hash_password("StrongPassword123")

    assert hashed_password != "StrongPassword123"
    assert verify_password("StrongPassword123", hashed_password)


def test_verify_password_rejects_wrong_password() -> None:
    hashed_password = hash_password("StrongPassword123")

    assert not verify_password("WrongPassword123", hashed_password)


def test_verify_password_rejects_invalid_hash() -> None:
    assert not verify_password("StrongPassword123", "invalid-hash")


def test_create_and_decode_access_token() -> None:
    session_id = str(uuid4())

    token = create_access_token(1, session_id)
    payload = decode_access_token(token)

    assert payload["sub"] == "1"
    assert payload["sid"] == session_id
    assert payload["type"] == "access"
    assert payload["jti"]
    assert payload["iat"]
    assert payload["exp"]


def test_create_and_decode_refresh_token() -> None:
    session_id = str(uuid4())

    token = create_refresh_token(1, session_id)
    payload = decode_refresh_token(token)

    assert payload["sub"] == "1"
    assert payload["sid"] == session_id
    assert payload["type"] == "refresh"
    assert payload["jti"]
    assert payload["iat"]
    assert payload["exp"]


def test_access_decoder_rejects_refresh_token() -> None:
    token = create_refresh_token(1, str(uuid4()))

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_refresh_decoder_rejects_access_token() -> None:
    token = create_access_token(1, str(uuid4()))

    with pytest.raises(jwt.InvalidTokenError):
        decode_refresh_token(token)


def test_decode_access_token_rejects_expired_token() -> None:
    now = datetime.now(UTC)
    payload = {
        "sub": "1",
        "sid": str(uuid4()),
        "jti": str(uuid4()),
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=5),
        "type": "access",
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


@pytest.mark.parametrize(
    "claim, invalid_value",
    [
        ("sub", "abc"),
        ("sid", ""),
        ("jti", ""),
        ("iat", "not-a-timestamp"),
        ("exp", "not-a-timestamp"),
    ],
)
def test_decode_access_token_rejects_invalid_claims(
    claim: str,
    invalid_value: str,
) -> None:
    now = datetime.now(UTC)
    payload = {
        "sub": "1",
        "sid": str(uuid4()),
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(hours=1),
        "type": "access",
    }
    payload[claim] = invalid_value

    token = jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)
