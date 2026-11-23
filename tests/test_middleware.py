import logging
from uuid import UUID

import pytest


@pytest.mark.asyncio
async def test_request_middleware_generates_request_id(async_client):
    response = await async_client.get("/health")

    request_id = response.headers["x-request-id"]

    UUID(request_id)

    assert response.status_code == 200
    assert float(response.headers["x-process-time"]) >= 0


@pytest.mark.asyncio
async def test_request_middleware_preserves_incoming_request_id(async_client):
    request_id = "test-request-123"

    response = await async_client.get(
        "/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id


@pytest.mark.asyncio
async def test_request_middleware_logs_request(async_client, caplog):
    with caplog.at_level(logging.INFO):
        response = await async_client.get("/health")

    assert response.status_code == 200
    assert "Request started" in caplog.text
    assert "Request completed" in caplog.text
    assert "GET" in caplog.text
    assert "/health" in caplog.text
    assert "status_code=200" in caplog.text


@pytest.mark.asyncio
async def test_request_middleware_returns_request_id_on_not_found(
    async_client,
):
    response = await async_client.get("/route-does-not-exist")

    assert response.status_code == 404
    assert response.headers.get("x-request-id")
    assert float(response.headers["x-process-time"]) >= 0
