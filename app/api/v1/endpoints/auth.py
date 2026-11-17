from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.dependencies.auth import CurrentUserDep
from app.dependencies.common import get_user_service
from app.schemas.user import (
    ChangePassword,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.services.user_service import UserService

UserServiceDep = Annotated[UserService, Depends(get_user_service)]

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserRegister,
    service: UserServiceDep,
) -> UserRead:
    user = await service.register(user_data)

    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    login_data: UserLogin,
    service: UserServiceDep,
) -> TokenResponse:
    return await service.login(login_data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(
    refresh_data: RefreshRequest,
    service: UserServiceDep,
) -> TokenResponse:
    return await service.refresh(refresh_data)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    current: CurrentUserDep,
    service: UserServiceDep,
) -> Response:
    await service.logout(
        user_id=current.user.id,
        session_id=current.session_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def change_password(
    password_data: ChangePassword,
    current: CurrentUserDep,
    service: UserServiceDep,
) -> Response:
    await service.change_password(
        user_id=current.user.id,
        password_data=password_data,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
