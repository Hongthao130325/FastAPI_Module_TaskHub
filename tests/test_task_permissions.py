from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStatus, UserRole, WorkspaceRole
from app.models.project import Project
from app.models.user import User
from app.models.workspace_member import WorkspaceMember


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


async def test_editor_can_create_and_update_task(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    await grant_workspace_role(
        db_session,
        task_context["workspace_id"],
        another_user_context["user_id"],
        WorkspaceRole.EDITOR,
    )
    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    create_response = await async_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Editor Task",
        },
    )

    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    update_response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated by Editor"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated by Editor"


async def test_viewer_can_view_but_cannot_create_update_or_delete_task(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Owner Task",
        },
    )
    task_id = create_response.json()["id"]

    await grant_workspace_role(
        db_session,
        task_context["workspace_id"],
        another_user_context["user_id"],
        WorkspaceRole.VIEWER,
    )
    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    get_response = await async_client.get(f"/api/v1/tasks/{task_id}")
    create_response = await async_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Viewer Task",
        },
    )
    update_response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Viewer Update"},
    )
    delete_response = await async_client.delete(f"/api/v1/tasks/{task_id}")

    assert get_response.status_code == 200
    assert create_response.status_code == 403
    assert update_response.status_code == 403
    assert delete_response.status_code == 403


async def test_editor_can_delete_tasks_created_by_other_members(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    owner_task_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Owner Created Task",
        },
    )
    owner_task_id = owner_task_response.json()["id"]

    await grant_workspace_role(
        db_session,
        task_context["workspace_id"],
        another_user_context["user_id"],
        WorkspaceRole.EDITOR,
    )
    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    delete_other_member_task_response = await async_client.delete(
        f"/api/v1/tasks/{owner_task_id}"
    )
    editor_task_response = await async_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Editor Created Task",
        },
    )
    editor_task_id = editor_task_response.json()["id"]
    allowed_response = await async_client.delete(f"/api/v1/tasks/{editor_task_id}")

    assert delete_other_member_task_response.status_code == 204
    assert editor_task_response.status_code == 201
    assert allowed_response.status_code == 204


async def test_owner_can_delete_task_created_by_editor(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    owner_token = authenticated_client.headers["Authorization"]

    await grant_workspace_role(
        db_session,
        task_context["workspace_id"],
        another_user_context["user_id"],
        WorkspaceRole.EDITOR,
    )
    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    create_response = await async_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Editor Task",
        },
    )
    task_id = create_response.json()["id"]

    async_client.headers["Authorization"] = owner_token
    delete_response = await authenticated_client.delete(f"/api/v1/tasks/{task_id}")

    assert create_response.status_code == 201
    assert delete_response.status_code == 204


async def test_admin_can_access_and_delete_task_without_workspace_membership(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Owner Task",
        },
    )
    task_id = create_response.json()["id"]

    admin = await db_session.get(User, another_user_context["user_id"])
    assert admin is not None
    admin.role = UserRole.ADMIN
    await db_session.flush()

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    get_response = await async_client.get(f"/api/v1/tasks/{task_id}")
    list_response = await async_client.get(
        f"/api/v1/projects/{task_context['project_id']}/tasks"
    )
    delete_response = await async_client.delete(f"/api/v1/tasks/{task_id}")

    assert get_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert delete_response.status_code == 204


async def test_assignee_must_belong_to_project_workspace(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task With External Assignee",
            "assignee_id": another_user_context["user_id"],
        },
    )

    assert response.status_code == 400


async def test_assignee_can_be_member_of_same_workspace(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
):
    await grant_workspace_role(
        db_session,
        task_context["workspace_id"],
        another_user_context["user_id"],
        WorkspaceRole.VIEWER,
    )

    response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task With Workspace Assignee",
            "assignee_id": another_user_context["user_id"],
        },
    )

    assert response.status_code == 201
    assert response.json()["assignee_id"] == another_user_context["user_id"]


async def test_archived_project_rejects_all_task_writes(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task Before Archive",
        },
    )
    task_id = create_response.json()["id"]

    project = await db_session.get(Project, task_context["project_id"])
    assert project is not None
    project.status = ProjectStatus.ARCHIVED
    await db_session.flush()

    create_archived_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task After Archive",
        },
    )
    update_response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated Archived Task"},
    )
    delete_response = await authenticated_client.delete(f"/api/v1/tasks/{task_id}")

    assert create_response.status_code == 201
    assert create_archived_response.status_code == 409
    assert update_response.status_code == 409
    assert delete_response.status_code == 409
