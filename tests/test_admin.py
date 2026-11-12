from httpx import AsyncClient
from sqlalchemy import select

from app.main import app as fastapi_app
from app.models.user import User, UserRole
from tests.helpers import login_as


async def promote_to_admin(email: str) -> None:
    async with fastapi_app.state.test_sessionmaker() as session:
        user = await session.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = UserRole.ADMIN
        await session.commit()


async def test_admin_endpoint_rejects_regular_user(client: AsyncClient) -> None:
    headers = await login_as(client, "member@example.com")
    response = await client.get("/api/v1/admin/workspaces", headers=headers)
    assert response.status_code == 403


async def test_admin_can_list_every_workspace(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    await client.post("/api/v1/workspaces", json={"name": "Team A"}, headers=owner)

    admin = await login_as(client, "admin@example.com")
    await promote_to_admin("admin@example.com")
    admin = await login_as(client, "admin@example.com")

    response = await client.get("/api/v1/admin/workspaces", headers=admin)
    assert response.status_code == 200
    assert [workspace["name"] for workspace in response.json()] == ["Team A"]
