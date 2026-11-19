from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.dependencies.auth import CurrentUserDep
from app.dependencies.common import get_auth_service
from app.schemas.user import (
    ChangePassword,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.services.auth_service import AuthService

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        409: {"description": "Email is already registered"},
        422: {"description": "Request validation error"},
    },
)
async def register(
    user_data: UserRegister,
    service: AuthServiceDep,
) -> UserRead:
    user = await service.register(user_data)

    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user",
    responses={
        401: {"description": "Invalid email or password"},
        403: {"description": "User account is inactive"},
        422: {"description": "Request validation error"},
    },
)
async def login(
    login_data: UserLogin,
    service: AuthServiceDep,
) -> TokenResponse:
    return await service.login(login_data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh authentication tokens",
    responses={
        401: {"description": "Invalid, expired, or revoked refresh token"},
        403: {"description": "User account is inactive"},
        422: {"description": "Request validation error"},
    },
)
async def refresh(
    refresh_data: RefreshRequest,
    service: AuthServiceDep,
) -> TokenResponse:
    return await service.refresh(refresh_data)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out the current session",
    responses={
        401: {"description": "Invalid or expired access token"},
        403: {"description": "User account is inactive"},
    },
)
async def logout(
    current: CurrentUserDep,
    service: AuthServiceDep,
) -> Response:
    await service.logout(
        user=current.user,
        session_id=current.session_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the current user's password",
    responses={
        400: {
            "description": "Current password is incorrect or new password is unchanged"
        },
        401: {"description": "Invalid or expired access token"},
        403: {"description": "User account is inactive"},
        422: {"description": "Request validation error"},
    },
)
async def change_password(
    password_data: ChangePassword,
    current: CurrentUserDep,
    service: AuthServiceDep,
) -> Response:
    await service.change_password(
        user=current.user,
        password_data=password_data,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
