from httpx import AsyncClient


async def test_create_task_success(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "project_id": task_context["project_id"],
        "title": "Test Task",
        "description": "Task created by automated test",
    }

    response = await async_client.post("/api/v1/tasks", json=payload)

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["project_id"] == payload["project_id"]
    assert data["created_by"] == task_context["user_id"]
    assert data["status"] == "TODO"
    assert data["priority"] == "MEDIUM"
    assert data["assignee_id"] is None
    assert data["id"] > 0


async def test_create_task_with_invalid_project(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "project_id": 999999,
        "title": "Invalid Project Task",
    }

    response = await async_client.post("/api/v1/tasks", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


async def test_create_task_rejects_client_provided_creator(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "created_by": 999999,
            "title": "Client Provided Creator Task",
        },
    )

    assert response.status_code == 422


async def test_create_task_with_invalid_assignee(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "project_id": task_context["project_id"],
        "assignee_id": 999999,
        "title": "Invalid Assignee Task",
    }

    response = await async_client.post("/api/v1/tasks", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


async def test_get_all_tasks(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "project_id": task_context["project_id"],
        "title": "Task For Listing",
    }

    await async_client.post("/api/v1/tasks", json=payload)

    response = await async_client.get("/api/v1/tasks")

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == payload["title"]
    assert data["total"] == 1
    assert data["limit"] == 10
    assert data["offset"] == 0


async def test_get_all_tasks_with_limit_and_offset(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    for index in range(3):
        response = await async_client.post(
            "/api/v1/tasks",
            json={
                "project_id": task_context["project_id"],
                "title": f"Task {index + 1}",
            },
        )

        assert response.status_code == 201

    response = await async_client.get(
        "/api/v1/tasks",
        params={"limit": 2, "offset": 1},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 2
    assert [item["title"] for item in data["items"]] == [
        "Task 2",
        "Task 3",
    ]
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 1


async def test_get_all_tasks_with_empty_page(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task For Empty Page",
        },
    )

    response = await async_client.get(
        "/api/v1/tasks",
        params={"limit": 10, "offset": 10},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 1
    assert data["limit"] == 10
    assert data["offset"] == 10


async def test_get_all_tasks_with_invalid_limit(
    async_client: AsyncClient,
):
    response = await async_client.get(
        "/api/v1/tasks",
        params={"limit": 0},
    )

    assert response.status_code == 422


async def test_get_all_tasks_with_limit_exceeding_maximum(
    async_client: AsyncClient,
):
    response = await async_client.get(
        "/api/v1/tasks",
        params={"limit": 101},
    )

    assert response.status_code == 422


async def test_get_all_tasks_with_negative_offset(
    async_client: AsyncClient,
):
    response = await async_client.get(
        "/api/v1/tasks",
        params={"offset": -1},
    )

    assert response.status_code == 422


async def test_get_task_by_id(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "project_id": task_context["project_id"],
        "title": "Task For Detail",
    }

    create_response = await async_client.post(
        "/api/v1/tasks",
        json=payload,
    )

    task_id = create_response.json()["id"]

    response = await async_client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == task_id
    assert data["title"] == payload["title"]


async def test_get_task_by_invalid_id(
    async_client: AsyncClient,
):
    response = await async_client.get("/api/v1/tasks/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


async def test_update_task_success(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    payload = {
        "project_id": task_context["project_id"],
        "title": "Original Task",
    }

    create_response = await async_client.post(
        "/api/v1/tasks",
        json=payload,
    )

    task_id = create_response.json()["id"]

    update_response = await async_client.patch(
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
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task With Assignee",
        },
    )

    task_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assignee_id": None},
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] is None


async def test_update_task_with_invalid_assignee(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task For Invalid Assignee",
        },
    )

    task_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assignee_id": 999999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


async def test_update_task_with_invalid_id(
    async_client: AsyncClient,
):
    response = await async_client.patch(
        "/api/v1/tasks/999999",
        json={"title": "Updated Task"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


async def test_update_task_with_null_title(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task For Null Validation",
        },
    )

    task_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": None},
    )

    assert response.status_code == 422


async def test_delete_task_success(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task For Deletion",
        },
    )

    task_id = create_response.json()["id"]

    delete_response = await async_client.delete(
        f"/api/v1/tasks/{task_id}",
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = await async_client.get(
        f"/api/v1/tasks/{task_id}",
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Task not found"


async def test_delete_task_with_invalid_id(
    async_client: AsyncClient,
):
    response = await async_client.delete("/api/v1/tasks/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


async def test_create_task_with_future_aware_due_date(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task With Future Due Date",
            "due_date": "2099-12-01T10:00:00+07:00",
        },
    )

    assert response.status_code == 201
    assert response.json()["due_date"] is not None


async def test_create_task_with_naive_due_date(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task With Naive Due Date",
            "due_date": "2099-12-01T10:00:00",
        },
    )

    assert response.status_code == 422


async def test_create_task_with_past_due_date(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task With Past Due Date",
            "due_date": "2000-01-01T10:00:00+07:00",
        },
    )

    assert response.status_code == 422


async def test_update_task_with_future_aware_due_date(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task For Future Due Date Update",
        },
    )

    task_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"due_date": "2099-12-01T10:00:00+07:00"},
    )

    assert response.status_code == 200
    assert response.json()["due_date"] is not None


async def test_update_task_with_naive_due_date(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task For Naive Due Date Update",
        },
    )

    task_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"due_date": "2099-12-01T10:00:00"},
    )

    assert response.status_code == 422


async def test_update_task_with_past_due_date(
    async_client: AsyncClient,
    task_context: dict[str, int],
):
    create_response = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": task_context["project_id"],
            "title": "Task For Past Due Date Update",
        },
    )

    task_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"due_date": "2000-01-01T10:00:00+07:00"},
    )

    assert response.status_code == 422
