from httpx import AsyncClient

from app.models.enums import UserRole
from app.models.user import User


async def test_owner_can_create_project(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "workspace_id": task_context["workspace_id"],
        "name": "New Project",
        "description": "Project description",
    }

    response = await authenticated_client.post(
        "/api/v1/projects",
        json=payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["workspace_id"] == task_context["workspace_id"]
    assert data["status"] == "ACTIVE"
    assert data["id"] > 0


async def test_owner_can_get_and_update_project(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    project_id = task_context["project_id"]

    get_response = await authenticated_client.get(
        f"/api/v1/projects/{project_id}",
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == project_id

    update_response = await authenticated_client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "name": "Updated Project",
            "description": "Updated description",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Project"
    assert update_response.json()["description"] == "Updated description"


async def test_owner_can_archive_project(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    project_id = task_context["project_id"]

    response = await authenticated_client.post(
        f"/api/v1/projects/{project_id}/archive",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ARCHIVED"


async def test_owner_cannot_update_project_with_empty_payload(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.patch(
        f"/api/v1/projects/{task_context['project_id']}",
        json={},
    )

    assert response.status_code == 400


async def test_editor_can_manage_project(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    add_response = await authenticated_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={
            "email": "another-task-test@example.com",
            "role": "EDITOR",
        },
    )

    assert add_response.status_code == 201

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    create_response = await async_client.post(
        "/api/v1/projects",
        json={
            "workspace_id": task_context["workspace_id"],
            "name": "Editor Project",
        },
    )

    assert create_response.status_code == 201

    project_id = create_response.json()["id"]

    update_response = await async_client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Editor Updated Project"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Editor Updated Project"

    archive_response = await async_client.post(
        f"/api/v1/projects/{project_id}/archive",
    )

    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "ARCHIVED"


async def test_viewer_can_view_but_cannot_manage_project(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    add_response = await authenticated_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={
            "email": "another-task-test@example.com",
            "role": "VIEWER",
        },
    )

    assert add_response.status_code == 201

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    project_id = task_context["project_id"]

    get_response = await async_client.get(
        f"/api/v1/projects/{project_id}",
    )

    assert get_response.status_code == 200

    list_response = await async_client.get(
        f"/api/v1/projects/workspace/{task_context['workspace_id']}",
    )

    assert list_response.status_code == 200
    assert any(project["id"] == project_id for project in list_response.json()["items"])

    create_response = await async_client.post(
        "/api/v1/projects",
        json={
            "workspace_id": task_context["workspace_id"],
            "name": "Viewer Project",
        },
    )

    assert create_response.status_code == 403

    update_response = await async_client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Viewer Updated Project"},
    )

    assert update_response.status_code == 403

    archive_response = await async_client.post(
        f"/api/v1/projects/{project_id}/archive",
    )

    assert archive_response.status_code == 403


async def test_non_member_cannot_access_project(
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_token: str,
):
    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    response = await async_client.get(
        f"/api/v1/projects/{task_context['project_id']}",
    )

    assert response.status_code == 403


async def test_non_member_cannot_get_workspace_projects(
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_token: str,
):
    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    response = await async_client.get(
        f"/api/v1/projects/workspace/{task_context['workspace_id']}",
    )

    assert response.status_code == 403


async def test_admin_can_manage_project_without_membership(
    authenticated_client: AsyncClient,
    db_session,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
):
    admin_user = await db_session.get(User, task_context["user_id"])
    assert admin_user is not None

    admin_user.role = UserRole.ADMIN

    workspace_id = another_user_context["workspace_id"]
    project_id = another_user_context["project_id"]

    list_response = await authenticated_client.get("/api/v1/projects")

    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 2

    create_response = await authenticated_client.post(
        "/api/v1/projects",
        json={
            "workspace_id": workspace_id,
            "name": "Admin Project",
        },
    )

    assert create_response.status_code == 201

    update_response = await authenticated_client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Admin Updated Project"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Admin Updated Project"

    archive_response = await authenticated_client.post(
        f"/api/v1/projects/{project_id}/archive",
    )

    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "ARCHIVED"


async def test_create_project_in_nonexistent_workspace_returns_404(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.post(
        "/api/v1/projects",
        json={
            "workspace_id": 999999,
            "name": "Invalid Project",
        },
    )

    assert response.status_code == 404


async def test_get_nonexistent_project_returns_404(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.get(
        "/api/v1/projects/999999",
    )

    assert response.status_code == 404
