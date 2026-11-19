from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import CurrentUserDep
from app.dependencies.common import get_project_service
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])

ProjectServiceDep = Annotated[
    ProjectService,
    Depends(get_project_service),
]


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
async def create_project(
    project_data: ProjectCreate,
    service: ProjectServiceDep,
    current_user: CurrentUserDep,
) -> ProjectResponse:
    project = await service.create_project(
        project_data.workspace_id,
        project_data.name,
        project_data.description,
        current_user.user,
    )

    return ProjectResponse.model_validate(project)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="Get all accessible projects",
)
async def get_all_projects(
    service: ProjectServiceDep,
    current_user: CurrentUserDep,
) -> ProjectListResponse:
    projects = await service.get_all_projects(current_user.user)

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(project) for project in projects],
    )


@router.get(
    "/workspace/{workspace_id}",
    response_model=ProjectListResponse,
    summary="Get projects by workspace",
)
async def get_projects_by_workspace(
    workspace_id: int,
    service: ProjectServiceDep,
    current_user: CurrentUserDep,
) -> ProjectListResponse:
    projects = await service.get_projects_by_workspace(
        workspace_id,
        current_user.user,
    )

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(project) for project in projects],
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project by ID",
)
async def get_project_by_id(
    project_id: int,
    service: ProjectServiceDep,
    current_user: CurrentUserDep,
) -> ProjectResponse:
    project = await service.get_project_by_id(
        project_id,
        current_user.user,
    )

    return ProjectResponse.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    service: ProjectServiceDep,
    current_user: CurrentUserDep,
) -> ProjectResponse:
    project = await service.update_project(
        project_id,
        project_data.model_dump(exclude_unset=True),
        current_user.user,
    )

    return ProjectResponse.model_validate(project)


@router.post(
    "/{project_id}/archive",
    response_model=ProjectResponse,
    summary="Archive a project",
)
async def archive_project(
    project_id: int,
    service: ProjectServiceDep,
    current_user: CurrentUserDep,
) -> ProjectResponse:
    project = await service.archive_project(
        project_id,
        current_user.user,
    )

    return ProjectResponse.model_validate(project)
