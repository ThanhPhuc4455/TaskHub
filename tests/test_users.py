from httpx import AsyncClient

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


async def test_change_password_revokes_refresh_tokens(auth_client: AsyncClient) -> None:
    login = await auth_client.post(
        "/api/v1/auth/login",
        data={"username": "owner@example.com", "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]

    response = await auth_client.post(
        f"{ME}/change-password",
        json={"current_password": "password123", "new_password": "newpassword456"},
    )
    assert response.status_code == 204
    assert (
        await auth_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    ).status_code == 401
