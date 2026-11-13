from httpx import AsyncClient

PASSWORD = "password123"


async def login_as(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "User"},
    )
    response = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def user_id_of(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.get("/api/v1/users/me", headers=headers)
    return int(response.json()["id"])
