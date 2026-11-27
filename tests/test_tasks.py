from httpx import AsyncClient


async def test_create_task_success(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "title": "Test Task",
        "description": "Task created by automated test",
    }

    response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks", json=payload
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["project_id"] == task_context["project_id"]
    assert data["created_by"] == task_context["user_id"]
    assert data["status"] == "TODO"
    assert data["priority"] == "MEDIUM"
    assert data["assignee_id"] is None
    assert data["id"] > 0


async def test_create_task_with_invalid_project(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "title": "Invalid Project Task",
    }

    response = await authenticated_client.post(
        "/api/v1/projects/999999/tasks", json=payload
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


async def test_create_task_rejects_client_provided_creator(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "created_by": 999999,
            "title": "Client Provided Creator Task",
        },
    )

    assert response.status_code == 422


async def test_create_task_with_invalid_assignee(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "assignee_id": 999999,
        "title": "Invalid Assignee Task",
    }

    response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks", json=payload
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


async def test_get_all_tasks(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "title": "Task For Listing",
    }

    await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks", json=payload
    )

    response = await authenticated_client.get(
        f"/api/v1/projects/{task_context['project_id']}/tasks"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == payload["title"]
    assert data["total"] == 1
    assert data["limit"] == 20
    assert data["page"] == 1


async def test_get_all_tasks_with_limit_and_offset(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    for index in range(3):
        response = await authenticated_client.post(
            f"/api/v1/projects/{task_context['project_id']}/tasks",
            json={
                "title": f"Task {index + 1}",
            },
        )

        assert response.status_code == 201

    response = await authenticated_client.get(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        params={"limit": 2, "page": 2},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1
    assert [item["title"] for item in data["items"]] == ["Task 3"]
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["page"] == 2


async def test_get_all_tasks_with_empty_page(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task For Empty Page",
        },
    )

    response = await authenticated_client.get(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        params={"limit": 10, "page": 2},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 1
    assert data["limit"] == 10
    assert data["page"] == 2


async def test_get_all_tasks_with_invalid_limit(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.get(
        "/api/v1/projects/1/tasks",
        params={"limit": 0},
    )

    assert response.status_code == 422


async def test_get_all_tasks_with_limit_exceeding_maximum(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.get(
        "/api/v1/projects/1/tasks",
        params={"limit": 101},
    )

    assert response.status_code == 422


async def test_get_all_tasks_with_invalid_page(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.get(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        params={"page": 0},
    )

    assert response.status_code == 422


async def test_get_task_by_id(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "title": "Task For Detail",
    }

    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json=payload,
    )

    task_id = create_response.json()["id"]

    response = await authenticated_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == task_id
    assert data["title"] == payload["title"]


async def test_get_task_by_invalid_id(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.get("/api/v1/tasks/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


async def test_update_task_success(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "title": "Original Task",
    }

    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json=payload,
    )

    task_id = create_response.json()["id"]

    update_response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": "Updated Task",
            "priority": "HIGH",
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()

    assert data["id"] == task_id
    assert data["title"] == "Updated Task"
    assert data["priority"] == "HIGH"


async def test_update_task_clear_assignee(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task With Assignee",
        },
    )

    task_id = create_response.json()["id"]

    response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assignee_id": None},
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] is None


async def test_update_task_with_invalid_assignee(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task For Invalid Assignee",
        },
    )

    task_id = create_response.json()["id"]

    response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assignee_id": 999999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


async def test_update_task_with_invalid_id(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.patch(
        "/api/v1/tasks/999999",
        json={"title": "Updated Task"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


async def test_update_task_with_null_title(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task For Null Validation",
        },
    )

    task_id = create_response.json()["id"]

    response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": None},
    )

    assert response.status_code == 422


async def test_delete_task_success(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task For Deletion",
        },
    )

    task_id = create_response.json()["id"]

    delete_response = await authenticated_client.delete(
        f"/api/v1/tasks/{task_id}",
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = await authenticated_client.get(
        f"/api/v1/tasks/{task_id}",
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Task not found"


async def test_delete_task_with_invalid_id(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.delete("/api/v1/tasks/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


async def test_create_task_with_future_aware_due_date(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task With Future Due Date",
            "due_date": "2099-12-01T10:00:00+07:00",
        },
    )

    assert response.status_code == 201
    assert response.json()["due_date"] is not None


async def test_create_task_with_naive_due_date(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task With Naive Due Date",
            "due_date": "2099-12-01T10:00:00",
        },
    )

    assert response.status_code == 422


async def test_create_task_with_past_due_date(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task With Past Due Date",
            "due_date": "2000-01-01T10:00:00+07:00",
        },
    )

    assert response.status_code == 422


async def test_update_task_with_future_aware_due_date(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task For Future Due Date Update",
        },
    )

    task_id = create_response.json()["id"]

    response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"due_date": "2099-12-01T10:00:00+07:00"},
    )

    assert response.status_code == 200
    assert response.json()["due_date"] is not None


async def test_update_task_with_naive_due_date(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task For Naive Due Date Update",
        },
    )

    task_id = create_response.json()["id"]

    response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"due_date": "2099-12-01T10:00:00"},
    )

    assert response.status_code == 422


async def test_update_task_with_past_due_date(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Task For Past Due Date Update",
        },
    )

    task_id = create_response.json()["id"]

    response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"due_date": "2000-01-01T10:00:00+07:00"},
    )

    assert response.status_code == 422


async def test_get_all_tasks_requires_authentication(
    async_client: AsyncClient,
):
    response = await async_client.get("/api/v1/projects/1/tasks")

    assert response.status_code == 401


async def test_create_task_requires_authentication(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await async_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Unauthenticated Task",
        },
    )

    assert response.status_code == 401


async def test_get_task_requires_authentication(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Unauthenticated Access Task",
        },
    )
    assert create_response.status_code == 201

    task_id = create_response.json()["id"]
    async_client.headers.pop("Authorization", None)

    response = await async_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 401


async def test_update_task_requires_authentication(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Unauthenticated Update Task",
        },
    )
    assert create_response.status_code == 201

    task_id = create_response.json()["id"]
    async_client.headers.pop("Authorization", None)

    response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Unauthorized Update"},
    )

    assert response.status_code == 401


async def test_delete_task_requires_authentication(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Unauthenticated Delete Task",
        },
    )
    assert create_response.status_code == 201

    task_id = create_response.json()["id"]
    async_client.headers.pop("Authorization", None)

    response = await async_client.delete(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 401


async def test_create_task_forbidden_for_another_users_project(
    authenticated_client: AsyncClient,
    another_user_context: dict[str, int],
):
    response = await authenticated_client.post(
        f"/api/v1/projects/{another_user_context['project_id']}/tasks",
        json={
            "title": "Forbidden Task",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == ("Project not found")


async def test_get_task_returns_not_found_for_another_user(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Private Task",
        },
    )

    task_id = create_response.json()["id"]

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    response = await async_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


async def test_update_task_returns_not_found_for_another_user(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Private Task",
        },
    )

    task_id = create_response.json()["id"]

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Unauthorized Update"},
    )

    assert response.status_code == 404


async def test_delete_task_returns_not_found_for_another_user(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    create_response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Private Task",
        },
    )

    task_id = create_response.json()["id"]

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    response = await async_client.delete(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 404


async def test_get_all_tasks_hides_another_users_project(
    authenticated_client: AsyncClient,
    async_client: AsyncClient,
    task_context: dict[str, int],
    another_user_context: dict[str, int],
    another_user_token: str,
):
    await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "User One Task",
        },
    )

    async_client.headers["Authorization"] = f"Bearer {another_user_token}"

    response = await async_client.get(
        f"/api/v1/projects/{task_context['project_id']}/tasks"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == "Project not found"


async def test_get_all_tasks_with_filters(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
):
    assignee_id = task_context["user_id"]
    project_url = f"/api/v1/projects/{task_context['project_id']}/tasks"

    tasks = [
        {
            "title": "TODO LOW Assigned",
            "priority": "LOW",
            "assignee_id": assignee_id,
        },
        {
            "title": "DONE HIGH Assigned",
            "priority": "HIGH",
            "assignee_id": assignee_id,
        },
        {
            "title": "TODO HIGH Assigned",
            "priority": "HIGH",
            "assignee_id": assignee_id,
        },
        {
            "title": "TODO HIGH Unassigned",
            "priority": "HIGH",
        },
    ]

    created_task_ids = []

    for payload in tasks:
        response = await authenticated_client.post(project_url, json=payload)
        assert response.status_code == 201
        created_task_ids.append(response.json()["id"])

    update_response = await authenticated_client.patch(
        f"/api/v1/tasks/{created_task_ids[1]}",
        json={"status": "DONE"},
    )
    assert update_response.status_code == 200

    status_response = await authenticated_client.get(
        project_url,
        params={"status": "TODO"},
    )
    multiple_status_response = await authenticated_client.get(
        project_url,
        params=[("status", "TODO"), ("status", "DONE")],
    )
    priority_response = await authenticated_client.get(
        project_url,
        params={"priority": "HIGH"},
    )
    assignee_response = await authenticated_client.get(
        project_url,
        params={"assignee_id": assignee_id},
    )
    combined_response = await authenticated_client.get(
        project_url,
        params={
            "status": "TODO",
            "priority": "HIGH",
            "assignee_id": assignee_id,
        },
    )

    for response in (
        status_response,
        multiple_status_response,
        priority_response,
        assignee_response,
        combined_response,
    ):
        assert response.status_code == 200

    assert status_response.json()["total"] == 3
    assert multiple_status_response.json()["total"] == 4
    assert priority_response.json()["total"] == 3
    assert assignee_response.json()["total"] == 3

    combined_data = combined_response.json()
    assert combined_data["total"] == 1
    assert combined_data["items"][0]["title"] == "TODO HIGH Assigned"


async def test_task_list_cache_is_invalidated_after_mutations(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
    fake_redis,
):
    project_id = task_context["project_id"]
    project_url = f"/api/v1/projects/{project_id}/tasks"
    cache_pattern = f"tasks:project:{project_id}:*"

    create_response = await authenticated_client.post(
        project_url,
        json={"title": "Initial Cached Task"},
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    get_response = await authenticated_client.get(project_url)
    assert get_response.status_code == 200
    assert len(await fake_redis.keys(cache_pattern)) == 1

    create_response = await authenticated_client.post(
        project_url,
        json={"title": "Another Task"},
    )
    assert create_response.status_code == 201
    assert await fake_redis.keys(cache_pattern) == []

    get_response = await authenticated_client.get(project_url)
    assert get_response.status_code == 200
    assert len(await fake_redis.keys(cache_pattern)) == 1

    update_response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated Cached Task"},
    )
    assert update_response.status_code == 200
    assert await fake_redis.keys(cache_pattern) == []

    get_response = await authenticated_client.get(project_url)
    assert get_response.status_code == 200
    assert len(await fake_redis.keys(cache_pattern)) == 1

    delete_response = await authenticated_client.delete(f"/api/v1/tasks/{task_id}")
    assert delete_response.status_code == 204
    assert await fake_redis.keys(cache_pattern) == []


async def test_task_assignment_schedules_email_notification(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
    db_session,
    monkeypatch,
):
    from app.models.enums import WorkspaceRole
    from app.models.user import User
    from app.models.workspace_member import WorkspaceMember
    from app.services import task_service

    notifications = []

    async def capture_email(**kwargs):
        notifications.append(kwargs)

    monkeypatch.setattr(
        task_service,
        "send_task_assigned_email",
        capture_email,
    )

    first_assignee = User(
        email="first-assignee@example.com",
        full_name="First Assignee",
        hashed_password="test-hash",
    )
    second_assignee = User(
        email="second-assignee@example.com",
        full_name="Second Assignee",
        hashed_password="test-hash",
    )
    db_session.add_all([first_assignee, second_assignee])
    await db_session.flush()

    db_session.add_all(
        [
            WorkspaceMember(
                workspace_id=task_context["workspace_id"],
                user_id=first_assignee.id,
                role=WorkspaceRole.EDITOR,
            ),
            WorkspaceMember(
                workspace_id=task_context["workspace_id"],
                user_id=second_assignee.id,
                role=WorkspaceRole.EDITOR,
            ),
        ]
    )
    await db_session.flush()

    response = await authenticated_client.post(
        f"/api/v1/projects/{task_context['project_id']}/tasks",
        json={
            "title": "Assigned Task",
            "assignee_id": first_assignee.id,
        },
    )

    assert response.status_code == 201
    task_id = response.json()["id"]
    assert len(notifications) == 1
    assert notifications[0] == {
        "to_email": first_assignee.email,
        "recipient_name": first_assignee.full_name,
        "task_title": "Assigned Task",
        "task_id": task_id,
    }

    response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assignee_id": second_assignee.id},
    )

    assert response.status_code == 200
    assert len(notifications) == 2
    assert notifications[1]["to_email"] == second_assignee.email

    response = await authenticated_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated Assigned Task"},
    )

    assert response.status_code == 200
    assert len(notifications) == 2


async def test_task_list_returns_cached_data_without_database_query(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
    monkeypatch,
):
    from app.repositories.task_repository import TaskRepository

    project_url = f"/api/v1/projects/{task_context['project_id']}/tasks"

    create_response = await authenticated_client.post(
        project_url,
        json={"title": "Cached Task"},
    )
    assert create_response.status_code == 201

    first_response = await authenticated_client.get(project_url)
    assert first_response.status_code == 200
    first_data = first_response.json()

    async def fail_database_query(*args, **kwargs):
        raise AssertionError("Database should not be queried on a cache hit")

    monkeypatch.setattr(
        TaskRepository,
        "get_all_for_project",
        fail_database_query,
    )

    second_response = await authenticated_client.get(project_url)

    assert second_response.status_code == 200
    assert second_response.json() == first_data


async def test_task_list_handles_redis_get_and_set_failures(
    authenticated_client: AsyncClient,
    task_context: dict[str, int],
    monkeypatch,
):
    from redis.exceptions import ConnectionError as RedisConnectionError

    from app.services.cache_service import CacheService

    project_url = f"/api/v1/projects/{task_context['project_id']}/tasks"

    create_response = await authenticated_client.post(
        project_url,
        json={"title": "Database Fallback Task"},
    )
    assert create_response.status_code == 201

    async def fail_cache_operation(*args, **kwargs):
        raise RedisConnectionError("Redis unavailable")

    monkeypatch.setattr(CacheService, "get", fail_cache_operation)
    monkeypatch.setattr(CacheService, "set", fail_cache_operation)

    response = await authenticated_client.get(project_url)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Database Fallback Task"
