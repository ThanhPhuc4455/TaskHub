import logging

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app as fastapi_app


async def test_request_id_is_preserved_or_regenerated(client: AsyncClient) -> None:
    preserved = await client.get("/health", headers={"X-Request-ID": "trace-123"})
    regenerated = await client.get("/health", headers={"X-Request-ID": "not valid"})
    too_long = await client.get("/health", headers={"X-Request-ID": "x" * 129})

    assert preserved.headers["X-Request-ID"] == "trace-123"
    assert regenerated.headers["X-Request-ID"] != "not valid"
    assert too_long.headers["X-Request-ID"] != "x" * 129
    assert regenerated.headers["X-Request-ID"]
    assert too_long.headers["X-Request-ID"]


async def test_request_logging_contains_safe_metadata(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app.core.middleware")
    response = await client.get(
        "/health",
        headers={
            "X-Request-ID": "safe-1",
            "Authorization": "Bearer secret-token",
        },
    )

    assert response.status_code == 200
    assert "request_id=safe-1" in caplog.text
    assert "method=GET" in caplog.text
    assert "path=/health" in caplog.text
    assert "status=200" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "secret-token" not in caplog.text


async def test_error_responses_keep_detail_and_add_request_id(
    auth_client: AsyncClient,
) -> None:
    not_found = await auth_client.get(
        "/api/v1/workspaces/999999", headers={"X-Request-ID": "error-404"}
    )
    invalid = await auth_client.post(
        "/api/v1/workspaces", json={"name": None}, headers={"X-Request-ID": "error-422"}
    )

    assert not_found.status_code == 404
    assert not_found.json()["detail"] == "Workspace 999999 not found"
    assert not_found.json()["request_id"] == "error-404"
    assert not_found.json()["code"] == "application_error"
    assert invalid.status_code == 422
    assert invalid.json()["detail"]
    assert invalid.json()["request_id"] == "error-422"
    assert invalid.json()["code"] == "validation_error"


async def test_unhandled_exception_is_masked_and_logged(client: AsyncClient) -> None:
    async def crash() -> None:
        raise RuntimeError("secret internal failure")

    fastapi_app.add_api_route("/__test__/crash", crash, methods=["GET"])
    transport = ASGITransport(app=fastapi_app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as isolated:
            response = await isolated.get("/__test__/crash", headers={"X-Request-ID": "error-500"})
    finally:
        fastapi_app.router.routes = [
            route
            for route in fastapi_app.router.routes
            if getattr(route, "path", None) != "/__test__/crash"
        ]

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "error-500"
    assert response.json()["detail"] == "Internal server error"
    assert response.json()["request_id"] == "error-500"
    assert "secret internal failure" not in response.text
