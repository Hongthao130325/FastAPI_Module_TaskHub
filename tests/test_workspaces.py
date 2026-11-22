from httpx import AsyncClient

from app.models.enums import UserRole
from app.models.user import User


async def test_create_workspace_success(
    authenticated_client: AsyncClient,
):
    payload = {"name": "New Workspace"}

    response = await authenticated_client.post(
        "/api/v1/workspaces",
        json=payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == payload["name"]
    assert data["owner_id"] > 0
    assert data["id"] > 0
    assert "created_at" in data


async def test_create_workspace_creates_owner_membership(
    authenticated_client: AsyncClient,
):
    create_response = await authenticated_client.post(
        "/api/v1/workspaces",
        json={"name": "Owner Membership Workspace"},
    )

    assert create_response.status_code == 201

    workspace_id = create_response.json()["id"]

    response = await authenticated_client.get(
        f"/api/v1/workspaces/{workspace_id}/members",
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["role"] == "OWNER"


async def test_get_all_workspaces_returns_user_workspaces(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.get("/api/v1/workspaces")

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == task_context["workspace_id"]
    assert data["total"] == 1
    assert data["limit"] == 10
    assert data["offset"] == 0


async def test_admin_can_get_all_workspaces_with_pagination(
    authenticated_client: AsyncClient,
    db_session,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
):
    admin_user = await db_session.get(User, task_context["user_id"])
    assert admin_user is not None

    admin_user.role = UserRole.ADMIN

    first_response = await authenticated_client.get(
        "/api/v1/workspaces",
        params={"limit": 1, "offset": 0},
    )

    second_response = await authenticated_client.get(
        "/api/v1/workspaces",
        params={"limit": 1, "offset": 1},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    assert first_data["total"] == 2
    assert second_data["total"] == 2
    assert first_data["limit"] == 1
    assert second_data["limit"] == 1
    assert first_data["offset"] == 0
    assert second_data["offset"] == 1
    assert len(first_data["items"]) == 1
    assert len(second_data["items"]) == 1
    assert first_data["items"][0]["id"] != second_data["items"][0]["id"]


async def test_get_all_workspaces_rejects_zero_limit(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.get(
        "/api/v1/workspaces",
        params={"limit": 0},
    )

    assert response.status_code == 422


async def test_get_all_workspaces_rejects_negative_offset(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.get(
        "/api/v1/workspaces",
        params={"offset": -1},
    )

    assert response.status_code == 422


async def test_get_workspace_by_id_success(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.get(
        f"/api/v1/workspaces/{task_context['workspace_id']}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == task_context["workspace_id"]


async def test_non_member_cannot_access_workspace(
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_token: str,
):
    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    response = await async_client.get(
        f"/api/v1/workspaces/{task_context['workspace_id']}",
    )

    assert response.status_code == 403


async def test_owner_can_update_workspace(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    workspace_id = task_context["workspace_id"]

    response = await authenticated_client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Updated Workspace"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Workspace"


async def test_owner_cannot_update_workspace_with_empty_payload(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    workspace_id = task_context["workspace_id"]

    response = await authenticated_client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={},
    )

    assert response.status_code == 400


async def test_non_owner_cannot_update_workspace(
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

    response = await async_client.patch(
        f"/api/v1/workspaces/{task_context['workspace_id']}",
        json={"name": "Unauthorized Update"},
    )

    assert response.status_code == 403


async def test_owner_can_delete_workspace(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    workspace_id = task_context["workspace_id"]

    response = await authenticated_client.delete(
        f"/api/v1/workspaces/{workspace_id}",
    )

    assert response.status_code == 204

    get_response = await authenticated_client.get(
        f"/api/v1/workspaces/{workspace_id}",
    )

    assert get_response.status_code == 404


async def test_owner_can_add_editor_to_workspace(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={
            "email": "another-task-test@example.com",
            "role": "EDITOR",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == another_user_context["user_id"]
    assert data["role"] == "EDITOR"


async def test_owner_can_add_viewer_by_default(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={"email": "another-task-test@example.com"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == another_user_context["user_id"]
    assert response.json()["role"] == "VIEWER"


async def test_owner_cannot_add_existing_member(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={"email": "task-test@example.com"},
    )

    assert response.status_code == 409


async def test_owner_cannot_add_nonexistent_user(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={"email": "unknown-user@example.com"},
    )

    assert response.status_code == 404


async def test_owner_can_get_workspace_members(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.get(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["user_id"] > 0
    assert data["items"][0]["role"] == "OWNER"


async def test_non_owner_member_can_get_workspace_members(
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

    response = await async_client.get(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 2
    assert any(
        item["user_id"] == another_user_context["user_id"] and item["role"] == "VIEWER"
        for item in data["items"]
    )


async def test_owner_can_remove_workspace_member(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
):
    add_response = await authenticated_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={"email": "another-task-test@example.com"},
    )

    assert add_response.status_code == 201

    response = await authenticated_client.delete(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members/"
        f"{another_user_context['user_id']}",
    )

    assert response.status_code == 204

    members_response = await authenticated_client.get(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
    )

    assert members_response.status_code == 200
    remaining_user_ids = [
        member["user_id"] for member in members_response.json()["items"]
    ]
    assert another_user_context["user_id"] not in remaining_user_ids


async def test_owner_cannot_remove_self_from_workspace(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.delete(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members/"
        f"{task_context['user_id']}",
    )

    assert response.status_code == 400


async def test_viewer_cannot_add_workspace_member(
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

    response = await async_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={"email": "task-test@example.com"},
    )

    assert response.status_code == 403


async def test_editor_cannot_add_workspace_member(
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

    response = await async_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={"email": "task-test@example.com"},
    )

    assert response.status_code == 403


async def test_viewer_cannot_remove_workspace_member(
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

    response = await async_client.delete(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members/"
        f"{task_context['user_id']}",
    )

    assert response.status_code == 403


async def test_owner_cannot_invite_member_with_owner_role(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members",
        json={
            "email": "another-task-test@example.com",
            "role": "OWNER",
        },
    )

    assert response.status_code == 422


async def test_owner_cannot_remove_nonexistent_member(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.delete(
        f"/api/v1/workspaces/{task_context['workspace_id']}/members/999999",
    )

    assert response.status_code == 404


async def test_get_nonexistent_workspace_returns_404(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.get(
        "/api/v1/workspaces/999999",
    )

    assert response.status_code == 404


async def test_non_owner_cannot_delete_workspace(
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

    response = await async_client.delete(
        f"/api/v1/workspaces/{task_context['workspace_id']}",
    )

    assert response.status_code == 403


async def test_admin_can_manage_workspace_without_membership(
    authenticated_client: AsyncClient,
    db_session,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
):
    admin_user = await db_session.get(User, task_context["user_id"])
    assert admin_user is not None

    admin_user.role = UserRole.ADMIN

    invited_user = User(
        email="admin-invited@example.com",
        full_name="Admin Invited User",
        hashed_password="test-hash",
    )

    db_session.add(invited_user)
    await db_session.flush()

    workspace_id = another_user_context["workspace_id"]

    list_response = await authenticated_client.get(
        "/api/v1/workspaces",
    )

    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 2
    assert list_response.json()["total"] == 2

    detail_response = await authenticated_client.get(
        f"/api/v1/workspaces/{workspace_id}",
    )

    assert detail_response.status_code == 200

    update_response = await authenticated_client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Admin Updated Workspace"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Admin Updated Workspace"

    add_response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "admin-invited@example.com"},
    )

    assert add_response.status_code == 201

    remove_response = await authenticated_client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{invited_user.id}",
    )

    assert remove_response.status_code == 204

    delete_response = await authenticated_client.delete(
        f"/api/v1/workspaces/{workspace_id}",
    )

    assert delete_response.status_code == 204
