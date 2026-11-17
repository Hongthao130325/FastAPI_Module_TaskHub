from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_refresh_token, verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def test_register_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    payload = {
        "email": "new-user@example.com",
        "full_name": "New User",
        "password": "StrongPass123",
    }

    response = await async_client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]
    assert data["role"] == "MEMBER"
    assert data["is_active"] is True
    assert data["id"] > 0
    assert "hashed_password" not in data

    user = await db_session.get(User, data["id"])

    assert user is not None
    assert user.hashed_password != payload["password"]
    assert verify_password(
        payload["password"],
        user.hashed_password,
    )


async def test_register_duplicate_email(async_client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "full_name": "Duplicate User",
        "password": "StrongPass123",
    }

    first_response = await async_client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    second_response = await async_client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Email is already registered"


async def test_register_cannot_assign_admin_role(
    async_client: AsyncClient,
):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "role-test@example.com",
            "full_name": "Role Test",
            "password": "StrongPass123",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "MEMBER"


async def test_register_with_invalid_data(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalid-email",
            "full_name": "Invalid User",
            "password": "123",
        },
    )

    assert response.status_code == 422


async def test_login_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    credentials = {
        "email": "login-success@example.com",
        "password": "StrongPass123",
    }

    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Login Success",
        },
    )

    assert register_response.status_code == 201

    response = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"

    user = await db_session.get(User, register_response.json()["id"])
    assert user is not None

    payload = decode_refresh_token(data["refresh_token"])

    refresh_token = await db_session.get(RefreshToken, payload["jti"])

    assert refresh_token is not None
    assert refresh_token.user_id == user.id
    assert refresh_token.session_id == payload["sid"]
    assert refresh_token.expires_at.timestamp() == payload["exp"]


async def test_login_with_unknown_email(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    assert response.headers["www-authenticate"] == "Bearer"


async def test_login_with_wrong_password(async_client: AsyncClient):
    credentials = {
        "email": "wrong-password@example.com",
        "password": "StrongPass123",
    }

    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Wrong Password",
        },
    )

    assert register_response.status_code == 201

    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": credentials["email"],
            "password": "WrongPass123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    assert response.headers["www-authenticate"] == "Bearer"


async def test_login_with_inactive_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    credentials = {
        "email": "inactive-user@example.com",
        "password": "StrongPass123",
    }

    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Inactive User",
        },
    )

    assert register_response.status_code == 201

    user = await db_session.get(User, register_response.json()["id"])
    assert user is not None

    user.is_active = False
    await db_session.flush()

    response = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is inactive"


async def test_refresh_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    credentials = {
        "email": "refresh-success@example.com",
        "password": "StrongPass123",
    }

    await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Refresh Success",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    assert login_response.status_code == 200

    old_refresh_token = login_response.json()["refresh_token"]
    old_payload = decode_refresh_token(old_refresh_token)

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["refresh_token"] != old_refresh_token

    new_payload = decode_refresh_token(data["refresh_token"])

    old_record = await db_session.get(RefreshToken, old_payload["jti"])
    new_record = await db_session.get(RefreshToken, new_payload["jti"])

    assert old_record is not None
    assert old_record.revoked_at is not None
    assert old_record.replaced_by_jti == new_payload["jti"]

    assert new_record is not None
    assert new_record.revoked_at is None
    assert new_record.user_id == old_record.user_id
    assert new_record.session_id == old_record.session_id


async def test_refresh_rejects_reused_token(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    credentials = {
        "email": "refresh-replay@example.com",
        "password": "StrongPass123",
    }

    await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Refresh Replay",
        },
    )

    first_login = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )
    second_login = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    old_refresh_token = first_login.json()["refresh_token"]
    second_refresh_token = second_login.json()["refresh_token"]

    first_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert first_response.status_code == 200

    new_payload = decode_refresh_token(
        first_response.json()["refresh_token"],
    )

    second_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert second_response.status_code == 401

    new_record = await db_session.get(RefreshToken, new_payload["jti"])

    assert new_record is not None
    assert new_record.revoked_at is not None

    other_session_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh_token},
    )

    assert other_session_response.status_code == 200


async def test_refresh_rejects_access_token(async_client: AsyncClient):
    credentials = {
        "email": "refresh-access-token@example.com",
        "password": "StrongPass123",
    }

    await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Refresh Access Token",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    access_token = login_response.json()["access_token"]

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401


async def test_refresh_rejects_inactive_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    credentials = {
        "email": "refresh-inactive@example.com",
        "password": "StrongPass123",
    }

    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Refresh Inactive",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    refresh_payload = decode_refresh_token(
        login_response.json()["refresh_token"],
    )

    user = await db_session.get(User, register_response.json()["id"])

    assert user is not None

    user.is_active = False
    await db_session.flush()

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": login_response.json()["refresh_token"],
        },
    )

    assert response.status_code == 403

    token_record = await db_session.get(
        RefreshToken,
        refresh_payload["jti"],
    )

    assert token_record is not None
    assert token_record.revoked_at is not None


async def test_refresh_rejects_invalid_token(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )

    assert response.status_code == 401


async def test_logout_revokes_only_current_session(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    credentials = {
        "email": "logout-session@example.com",
        "password": "StrongPass123",
    }

    await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Logout Session",
        },
    )

    first_login = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    second_login = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    first_data = first_login.json()
    second_data = second_login.json()

    first_payload = decode_refresh_token(first_data["refresh_token"])
    second_payload = decode_refresh_token(second_data["refresh_token"])

    response = await async_client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {first_data['access_token']}",
        },
    )

    assert response.status_code == 204
    assert response.content == b""

    revoked_access_response = await async_client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {first_data['access_token']}",
        },
    )

    assert revoked_access_response.status_code == 401

    first_record = await db_session.get(
        RefreshToken,
        first_payload["jti"],
    )

    second_record = await db_session.get(
        RefreshToken,
        second_payload["jti"],
    )

    assert first_record is not None
    assert first_record.revoked_at is not None

    assert second_record is not None
    assert second_record.revoked_at is None

    second_refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_data["refresh_token"]},
    )

    assert second_refresh_response.status_code == 200

    first_refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_data["refresh_token"]},
    )

    assert first_refresh_response.status_code == 401


async def test_logout_requires_access_token(async_client: AsyncClient):
    response = await async_client.post("/api/v1/auth/logout")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_logout_rejects_refresh_token(async_client: AsyncClient):
    credentials = {
        "email": "logout-refresh-token@example.com",
        "password": "StrongPass123",
    }

    await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Logout Refresh Token",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    refresh_token = login_response.json()["refresh_token"]

    response = await async_client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {refresh_token}",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_change_password_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    credentials = {
        "email": "change-password@example.com",
        "password": "StrongPass123",
    }
    new_password = "NewStrongPass456"

    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Change Password",
        },
    )
    assert register_response.status_code == 201

    first_login = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )
    second_login = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    assert first_login.status_code == 200
    assert second_login.status_code == 200

    first_data = first_login.json()
    second_data = second_login.json()

    first_payload = decode_refresh_token(first_data["refresh_token"])
    second_payload = decode_refresh_token(second_data["refresh_token"])

    response = await async_client.post(
        "/api/v1/auth/change-password",
        headers={
            "Authorization": f"Bearer {first_data['access_token']}",
        },
        json={
            "current_password": credentials["password"],
            "new_password": new_password,
        },
    )

    assert response.status_code == 204
    assert response.content == b""

    first_access_response = await async_client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {first_data['access_token']}",
        },
    )
    second_access_response = await async_client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {second_data['access_token']}",
        },
    )

    assert first_access_response.status_code == 401
    assert second_access_response.status_code == 401

    user = await db_session.get(User, register_response.json()["id"])

    assert user is not None
    assert verify_password(new_password, user.hashed_password)
    assert not verify_password(credentials["password"], user.hashed_password)

    first_record = await db_session.get(
        RefreshToken,
        first_payload["jti"],
    )
    second_record = await db_session.get(
        RefreshToken,
        second_payload["jti"],
    )

    assert first_record is not None
    assert first_record.revoked_at is not None

    assert second_record is not None
    assert second_record.revoked_at is not None

    old_password_login = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )
    new_password_login = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": credentials["email"],
            "password": new_password,
        },
    )

    assert old_password_login.status_code == 401
    assert new_password_login.status_code == 200

    old_refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_data["refresh_token"]},
    )

    assert old_refresh_response.status_code == 401


async def test_change_password_with_wrong_current_password(
    async_client: AsyncClient,
):
    credentials = {
        "email": "change-password-wrong@example.com",
        "password": "StrongPass123",
    }

    await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Change Password Wrong",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    response = await async_client.post(
        "/api/v1/auth/change-password",
        headers={
            "Authorization": (f"Bearer {login_response.json()['access_token']}"),
        },
        json={
            "current_password": "WrongPassword123",
            "new_password": "NewStrongPass456",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Current password is incorrect"


async def test_change_password_rejects_same_password(
    async_client: AsyncClient,
):
    credentials = {
        "email": "change-password-same@example.com",
        "password": "StrongPass123",
    }

    await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Change Password Same",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    response = await async_client.post(
        "/api/v1/auth/change-password",
        headers={
            "Authorization": (f"Bearer {login_response.json()['access_token']}"),
        },
        json={
            "current_password": credentials["password"],
            "new_password": credentials["password"],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "New password must be different from current password"
    )


async def test_change_password_requires_authentication(
    async_client: AsyncClient,
):
    response = await async_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "StrongPass123",
            "new_password": "NewStrongPass456",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_change_password_rejects_short_password(
    async_client: AsyncClient,
):
    credentials = {
        "email": "change-password-short@example.com",
        "password": "StrongPass123",
    }

    await async_client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "full_name": "Change Password Short",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        json=credentials,
    )

    response = await async_client.post(
        "/api/v1/auth/change-password",
        headers={
            "Authorization": (f"Bearer {login_response.json()['access_token']}"),
        },
        json={
            "current_password": credentials["password"],
            "new_password": "short",
        },
    )

    assert response.status_code == 422
