from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import CurrentUserDep
from app.dependencies.common import get_workspace_service
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceListResponse,
    WorkspaceMemberCreate,
    WorkspaceMemberListResponse,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

WorkspaceServiceDep = Annotated[
    WorkspaceService,
    Depends(get_workspace_service),
]


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    service: WorkspaceServiceDep,
    current_user: CurrentUserDep,
) -> WorkspaceResponse:
    workspace = await service.create_workspace(
        workspace_data.name,
        current_user.user,
    )

    return WorkspaceResponse.model_validate(workspace)


@router.get(
    "",
    response_model=WorkspaceListResponse,
    summary="Get all workspaces",
)
async def get_all_workspaces(
    service: WorkspaceServiceDep,
    current_user: CurrentUserDep,
) -> WorkspaceListResponse:
    workspaces = await service.get_all_workspaces(current_user.user)

    return WorkspaceListResponse(
        items=[WorkspaceResponse.model_validate(workspace) for workspace in workspaces],
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get a workspace by ID",
)
async def get_workspace_by_id(
    workspace_id: int,
    service: WorkspaceServiceDep,
    current_user: CurrentUserDep,
) -> WorkspaceResponse:
    workspace = await service.get_workspace_by_id(
        workspace_id,
        current_user.user,
    )

    return WorkspaceResponse.model_validate(workspace)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update a workspace",
)
async def update_workspace(
    workspace_id: int,
    workspace_data: WorkspaceUpdate,
    service: WorkspaceServiceDep,
    current_user: CurrentUserDep,
) -> WorkspaceResponse:
    workspace = await service.update_workspace(
        workspace_id,
        workspace_data.model_dump(exclude_unset=True),
        current_user.user,
    )

    return WorkspaceResponse.model_validate(workspace)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace",
)
async def delete_workspace(
    workspace_id: int,
    service: WorkspaceServiceDep,
    current_user: CurrentUserDep,
) -> None:
    await service.delete_workspace(workspace_id, current_user.user)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a workspace member",
)
async def add_workspace_member(
    workspace_id: int,
    member_data: WorkspaceMemberCreate,
    service: WorkspaceServiceDep,
    current_user: CurrentUserDep,
) -> WorkspaceMemberResponse:
    membership, member_user = await service.add_workspace_member(
        workspace_id,
        str(member_data.email),
        member_data.role,
        current_user.user,
    )

    return WorkspaceMemberResponse(
        user_id=member_user.id,
        email=member_user.email,
        full_name=member_user.full_name,
        role=membership.role,
    )


@router.get(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberListResponse,
    summary="Get workspace members",
)
async def get_workspace_members(
    workspace_id: int,
    service: WorkspaceServiceDep,
    current_user: CurrentUserDep,
) -> WorkspaceMemberListResponse:
    members = await service.get_workspace_members(
        workspace_id,
        current_user.user,
    )

    return WorkspaceMemberListResponse(
        items=[
            WorkspaceMemberResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=membership.role,
            )
            for membership, user in members
        ],
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a workspace member",
)
async def remove_workspace_member(
    workspace_id: int,
    user_id: int,
    service: WorkspaceServiceDep,
    current_user: CurrentUserDep,
) -> None:
    await service.remove_workspace_member(
        workspace_id,
        user_id,
        current_user.user,
    )
