from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, status

from app.dependencies.auth import CurrentUserDep
from app.dependencies.common import PaginationDep, get_comment_service
from app.schemas.comment import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    CommentUpdate,
)
from app.services.background_tasks import log_comment_created
from app.services.comment_service import CommentService

router = APIRouter(
    prefix="/tasks/{task_id}/comments",
    tags=["Comments"],
)

CommentServiceDep = Annotated[
    CommentService,
    Depends(get_comment_service),
]
TaskId = Annotated[int, Path(gt=0)]
CommentId = Annotated[int, Path(gt=0)]


@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a comment on a task",
)
async def create_comment(
    task_id: TaskId,
    comment_data: CommentCreate,
    service: CommentServiceDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> CommentResponse:
    comment = await service.create_comment(
        task_id,
        comment_data,
        current_user.user,
    )

    background_tasks.add_task(
        log_comment_created,
        comment_id=comment.id,
        task_id=task_id,
        author_id=current_user.user.id,
    )

    return CommentResponse.model_validate(comment)


@router.get(
    "",
    response_model=CommentListResponse,
    summary="Get comments of a task",
)
async def get_all_comments(
    task_id: TaskId,
    service: CommentServiceDep,
    current_user: CurrentUserDep,
    pagination: PaginationDep,
) -> CommentListResponse:
    comments, total = await service.get_all_comments(
        task_id,
        current_user.user,
        pagination,
    )

    return CommentListResponse(
        items=[CommentResponse.model_validate(comment) for comment in comments],
        total=total,
        page=pagination.page,
        limit=pagination.limit,
    )


@router.get(
    "/{comment_id}",
    response_model=CommentResponse,
    summary="Get a comment by ID",
)
async def get_comment_by_id(
    task_id: TaskId,
    comment_id: CommentId,
    service: CommentServiceDep,
    current_user: CurrentUserDep,
) -> CommentResponse:
    comment = await service.get_comment_by_id(
        task_id,
        comment_id,
        current_user.user,
    )

    return CommentResponse.model_validate(comment)


@router.patch(
    "/{comment_id}",
    response_model=CommentResponse,
    summary="Update a comment",
)
async def update_comment(
    task_id: TaskId,
    comment_id: CommentId,
    comment_data: CommentUpdate,
    service: CommentServiceDep,
    current_user: CurrentUserDep,
) -> CommentResponse:
    comment = await service.update_comment(
        task_id,
        comment_id,
        comment_data,
        current_user.user,
    )

    return CommentResponse.model_validate(comment)


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
)
async def delete_comment(
    task_id: TaskId,
    comment_id: CommentId,
    service: CommentServiceDep,
    current_user: CurrentUserDep,
) -> None:
    await service.delete_comment(
        task_id,
        comment_id,
        current_user.user,
    )
