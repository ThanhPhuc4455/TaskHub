from typing import cast

from httpx import AsyncClient

AUTH = "/api/v1/auth"
USER = {"email": "a@example.com", "password": "password123", "full_name": "A"}


async def login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post(f"{AUTH}/login", data={"username": email, "password": password})
    assert response.status_code == 200
    return cast(dict[str, str], response.json())


async def test_register_hides_password(client: AsyncClient) -> None:
    response = await client.post(f"{AUTH}/register", json=USER)
    assert response.status_code == 201
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()


async def test_register_duplicate_email_is_case_insensitive(client: AsyncClient) -> None:
    await client.post(f"{AUTH}/register", json=USER)
    duplicate = {**USER, "email": "A@Example.com"}
    assert (await client.post(f"{AUTH}/register", json=duplicate)).status_code == 409


async def test_register_rejects_blank_full_name(client: AsyncClient) -> None:
    response = await client.post(f"{AUTH}/register", json={**USER, "full_name": "   "})
    assert response.status_code == 422


async def test_register_rejects_password_over_72_bytes(client: AsyncClient) -> None:
    response = await client.post(f"{AUTH}/register", json={**USER, "password": "ệ" * 30})
    assert response.status_code == 422


async def test_password_whitespace_is_preserved(client: AsyncClient) -> None:
    padded = {**USER, "password": "  password123  "}
    await client.post(f"{AUTH}/register", json=padded)
    await login(client, USER["email"], "  password123  ")


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post(f"{AUTH}/register", json=USER)
    response = await client.post(
        f"{AUTH}/login", data={"username": USER["email"], "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_login_overlong_password_returns_401_not_500(client: AsyncClient) -> None:
    await client.post(f"{AUTH}/register", json=USER)
    response = await client.post(
        f"{AUTH}/login", data={"username": USER["email"], "password": "x" * 200}
    )
    assert response.status_code == 401


async def test_refresh_and_token_type_check(client: AsyncClient) -> None:
    await client.post(f"{AUTH}/register", json=USER)
    tokens = await login(client, USER["email"], USER["password"])
    ok = await client.post(f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert ok.status_code == 200
    bad = await client.post(f"{AUTH}/refresh", json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401
