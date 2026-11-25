from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.enums import ProjectStatus, WorkspaceRole
from app.models.label import Label
from app.models.project import Project
from app.models.task_label import TaskLabel
from app.models.workspace_member import WorkspaceMember


async def create_task(
    client: AsyncClient,
    project_id: int,
) -> int:
    response = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task For Label Comment Tests"},
    )

    assert response.status_code == 201

    return response.json()["id"]


async def create_label(
    client: AsyncClient,
    project_id: int,
    name: str = "Important",
) -> int:
    response = await client.post(
        f"/api/v1/projects/{project_id}/labels",
        json={
            "name": name,
            "color": "#FF5733",
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


async def grant_workspace_role(
    db_session: AsyncSession,
    workspace_id: int,
    user_id: int,
    role: WorkspaceRole,
) -> None:
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
    )
    await db_session.flush()


async def test_owner_can_create_update_and_delete_label(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    project_id = task_context["project_id"]

    create_response = await authenticated_client.post(
        f"/api/v1/projects/{project_id}/labels",
        json={
            "name": "Urgent",
            "color": "#FF0000",
        },
    )

    assert create_response.status_code == 201

    label_id = create_response.json()["id"]

    get_response = await authenticated_client.get(
        f"/api/v1/projects/{project_id}/labels/{label_id}",
    )

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Urgent"

    update_response = await authenticated_client.patch(
        f"/api/v1/projects/{project_id}/labels/{label_id}",
        json={"name": "Critical"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Critical"

    delete_response = await authenticated_client.delete(
        f"/api/v1/projects/{project_id}/labels/{label_id}",
    )

    assert delete_response.status_code == 204

    get_deleted_response = await authenticated_client.get(
        f"/api/v1/projects/{project_id}/labels/{label_id}",
    )

    assert get_deleted_response.status_code == 404


async def test_duplicate_label_attachment_returns_conflict(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )
    label_id = await create_label(
        authenticated_client,
        task_context["project_id"],
    )

    first_response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
    )
    second_response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
    )

    assert first_response.status_code == 204
    assert second_response.status_code == 409


async def test_detaching_unattached_label_returns_not_found(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )
    label_id = await create_label(
        authenticated_client,
        task_context["project_id"],
    )

    response = await authenticated_client.delete(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
    )

    assert response.status_code == 404


async def test_viewer_cannot_create_label_or_comment(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )

    await grant_workspace_role(
        db_session,
        task_context["workspace_id"],
        another_user_context["user_id"],
        WorkspaceRole.VIEWER,
    )

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    label_response = await async_client.post(
        f"/api/v1/projects/{task_context['project_id']}/labels",
        json={
            "name": "Viewer Label",
            "color": "#00FF00",
        },
    )

    comment_response = await async_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Viewer comment"},
    )

    assert label_response.status_code == 403
    assert comment_response.status_code == 403


async def test_editor_cannot_delete_another_users_comment(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )

    comment_response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Comment created by owner"},
    )

    assert comment_response.status_code == 201
    comment_id = comment_response.json()["id"]

    await grant_workspace_role(
        db_session,
        task_context["workspace_id"],
        another_user_context["user_id"],
        WorkspaceRole.EDITOR,
    )

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    delete_response = await async_client.delete(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}",
    )

    assert delete_response.status_code == 403


async def test_author_can_update_own_comment(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )

    comment_response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Original comment"},
    )

    assert comment_response.status_code == 201
    comment_id = comment_response.json()["id"]

    update_response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}",
        json={"content": "Updated comment"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["content"] == "Updated comment"


async def test_editor_cannot_update_another_users_comment(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )

    comment_response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Comment created by owner"},
    )

    assert comment_response.status_code == 201
    comment_id = comment_response.json()["id"]

    await grant_workspace_role(
        db_session,
        task_context["workspace_id"],
        another_user_context["user_id"],
        WorkspaceRole.EDITOR,
    )

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    update_response = await async_client.patch(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}",
        json={"content": "Unauthorized update"},
    )

    assert update_response.status_code == 403


async def test_archived_project_rejects_label_and_comment_writes(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )

    project = await db_session.get(
        Project,
        task_context["project_id"],
    )
    assert project is not None

    project.status = ProjectStatus.ARCHIVED
    await db_session.flush()

    label_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/labels",
        json={
            "name": "Archived Label",
            "color": "#0000FF",
        },
    )

    comment_response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Archived comment"},
    )

    assert label_response.status_code == 409
    assert comment_response.status_code == 409


async def test_label_and_comment_pagination_returns_correct_total(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    project_id = task_context["project_id"]
    task_id = await create_task(authenticated_client, project_id)

    for index in range(3):
        label_response = await authenticated_client.post(
            f"/api/v1/projects/{project_id}/labels",
            json={
                "name": f"Label {index}",
                "color": "#123456",
            },
        )
        comment_response = await authenticated_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": f"Comment {index}"},
        )

        assert label_response.status_code == 201
        assert comment_response.status_code == 201

    label_list_response = await authenticated_client.get(
        f"/api/v1/projects/{project_id}/labels",
        params={"page": 2, "limit": 2},
    )

    comment_list_response = await authenticated_client.get(
        f"/api/v1/tasks/{task_id}/comments",
        params={"page": 2, "limit": 2},
    )

    assert label_list_response.status_code == 200
    assert comment_list_response.status_code == 200

    label_data = label_list_response.json()
    comment_data = comment_list_response.json()

    assert label_data["total"] == 3
    assert len(label_data["items"]) == 1
    assert label_data["page"] == 2

    assert comment_data["total"] == 3
    assert len(comment_data["items"]) == 1
    assert comment_data["page"] == 2


async def test_non_member_cannot_access_labels_or_comments(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_token: str,
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    label_response = await async_client.get(
        f"/api/v1/projects/{task_context['project_id']}/labels",
    )

    task_response = await async_client.get(
        f"/api/v1/tasks/{task_id}/comments",
    )

    assert label_response.status_code == 404
    assert task_response.status_code == 404


async def test_label_from_another_project_cannot_be_attached_to_task(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )

    project_response = await authenticated_client.post(
        "/api/v1/projects",
        json={
            "workspace_id": task_context["workspace_id"],
            "name": "Another Project",
        },
    )

    assert project_response.status_code == 201

    another_project_id = project_response.json()["id"]
    label_id = await create_label(
        authenticated_client,
        another_project_id,
        name="Foreign Project Label",
    )

    response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
    )

    assert response.status_code == 400


async def test_delete_task_cascades_comments_and_task_labels(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
):
    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )
    label_id = await create_label(
        authenticated_client,
        task_context["project_id"],
    )

    attach_response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
    )
    comment_response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Comment for cascade test"},
    )

    assert attach_response.status_code == 204
    assert comment_response.status_code == 201

    delete_response = await authenticated_client.delete(
        f"/api/v1/tasks/{task_id}",
    )

    assert delete_response.status_code == 204

    comment_count = await db_session.scalar(
        select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
    )
    task_label_count = await db_session.scalar(
        select(func.count()).select_from(TaskLabel).where(TaskLabel.task_id == task_id)
    )
    label_count = await db_session.scalar(
        select(func.count()).select_from(Label).where(Label.id == label_id)
    )

    assert comment_count == 0
    assert task_label_count == 0
    assert label_count == 1


async def test_create_comment_schedules_background_event(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
    monkeypatch,
):
    from app.api.v1.endpoints import comments

    events = []

    def capture_comment_created(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr(
        comments,
        "log_comment_created",
        capture_comment_created,
    )

    task_id = await create_task(
        authenticated_client,
        task_context["project_id"],
    )

    response = await authenticated_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Comment with background event"},
    )

    assert response.status_code == 201
    assert len(events) == 1
    assert events[0] == {
        "comment_id": response.json()["id"],
        "task_id": task_id,
        "author_id": task_context["user_id"],
    }
