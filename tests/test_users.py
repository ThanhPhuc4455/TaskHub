from httpx import AsyncClient
from sqlalchemy import select

from app.main import app as fastapi_app
from app.models.user import User

ME = "/api/v1/users/me"


async def test_me_requires_token(client: AsyncClient) -> None:
    assert (await client.get(ME)).status_code == 401


async def test_read_me(auth_client: AsyncClient) -> None:
    response = await auth_client.get(ME)
    assert response.status_code == 200
    assert response.json()["email"] == "owner@example.com"
    assert "hashed_password" not in response.json()


async def test_update_me(auth_client: AsyncClient) -> None:
    response = await auth_client.patch(ME, json={"full_name": "New Name"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "New Name"


async def test_update_me_rejects_null_name(auth_client: AsyncClient) -> None:
    assert (await auth_client.patch(ME, json={"full_name": None})).status_code == 422


async def test_change_password(auth_client: AsyncClient) -> None:
    wrong = await auth_client.post(
        f"{ME}/change-password",
        json={"current_password": "not-the-password", "new_password": "newpassword456"},
    )
    assert wrong.status_code == 400

    ok = await auth_client.post(
        f"{ME}/change-password",
        json={"current_password": "password123", "new_password": "newpassword456"},
    )
    assert ok.status_code == 204

    login = await auth_client.post(
        "/api/v1/auth/login",
        data={"username": "owner@example.com", "password": "newpassword456"},
    )
    assert login.status_code == 200

    old_password_login = await auth_client.post(
        "/api/v1/auth/login",
        data={"username": "owner@example.com", "password": "password123"},
    )
    assert old_password_login.status_code == 401


async def test_inactive_user_cannot_refresh_or_read_profile(auth_client: AsyncClient) -> None:
    tokens = await auth_client.post(
        "/api/v1/auth/login",
        data={"username": "owner@example.com", "password": "password123"},
    )
    assert tokens.status_code == 200
    refresh_token = tokens.json()["refresh_token"]

    sessionmaker = fastapi_app.state.test_sessionmaker
    async with sessionmaker() as session:
        user = await session.scalar(select(User).where(User.email == "owner@example.com"))
        assert user is not None
        user.is_active = False
        await session.commit()

    refresh = await auth_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh.status_code == 401
    assert refresh.json()["detail"] == "Inactive user"

    profile = await auth_client.get(ME)
    assert profile.status_code == 401
    assert profile.json()["detail"] == "Inactive user"
