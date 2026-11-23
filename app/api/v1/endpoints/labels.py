from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.dependencies.auth import CurrentUserDep
from app.dependencies.common import PaginationDep, get_label_service
from app.schemas.label import (
    LabelCreate,
    LabelListResponse,
    LabelResponse,
    LabelUpdate,
)
from app.services.label_service import LabelService

router = APIRouter(tags=["Labels"])

LabelServiceDep = Annotated[
    LabelService,
    Depends(get_label_service),
]
ProjectId = Annotated[int, Path(gt=0)]
LabelId = Annotated[int, Path(gt=0)]
TaskId = Annotated[int, Path(gt=0)]


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a label in a project",
)
async def create_label(
    project_id: ProjectId,
    label_data: LabelCreate,
    service: LabelServiceDep,
    current_user: CurrentUserDep,
) -> LabelResponse:
    label = await service.create_label(
        project_id,
        label_data,
        current_user.user,
    )

    return LabelResponse.model_validate(label)


@router.get(
    "/projects/{project_id}/labels",
    response_model=LabelListResponse,
    summary="Get labels in a project",
)
async def get_all_labels(
    project_id: ProjectId,
    service: LabelServiceDep,
    current_user: CurrentUserDep,
    pagination: PaginationDep,
) -> LabelListResponse:
    labels, total = await service.get_all_labels(
        project_id,
        current_user.user,
        pagination,
    )

    return LabelListResponse(
        items=[LabelResponse.model_validate(label) for label in labels],
        total=total,
        page=pagination.page,
        limit=pagination.limit,
    )


@router.get(
    "/projects/{project_id}/labels/{label_id}",
    response_model=LabelResponse,
    summary="Get a label by ID",
)
async def get_label_by_id(
    project_id: ProjectId,
    label_id: LabelId,
    service: LabelServiceDep,
    current_user: CurrentUserDep,
) -> LabelResponse:
    label = await service.get_label_by_id(
        project_id,
        label_id,
        current_user.user,
    )

    return LabelResponse.model_validate(label)


@router.patch(
    "/projects/{project_id}/labels/{label_id}",
    response_model=LabelResponse,
    summary="Update a label",
)
async def update_label(
    project_id: ProjectId,
    label_id: LabelId,
    label_data: LabelUpdate,
    service: LabelServiceDep,
    current_user: CurrentUserDep,
) -> LabelResponse:
    label = await service.update_label(
        project_id,
        label_id,
        label_data,
        current_user.user,
    )

    return LabelResponse.model_validate(label)


@router.delete(
    "/projects/{project_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a label",
)
async def delete_label(
    project_id: ProjectId,
    label_id: LabelId,
    service: LabelServiceDep,
    current_user: CurrentUserDep,
) -> None:
    await service.delete_label(
        project_id,
        label_id,
        current_user.user,
    )


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Attach a label to a task",
)
async def attach_label_to_task(
    task_id: TaskId,
    label_id: LabelId,
    service: LabelServiceDep,
    current_user: CurrentUserDep,
) -> None:
    await service.attach_label_to_task(
        task_id,
        label_id,
        current_user.user,
    )


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Detach a label from a task",
)
async def detach_label_from_task(
    task_id: TaskId,
    label_id: LabelId,
    service: LabelServiceDep,
    current_user: CurrentUserDep,
) -> None:
    await service.detach_label_from_task(
        task_id,
        label_id,
        current_user.user,
    )
