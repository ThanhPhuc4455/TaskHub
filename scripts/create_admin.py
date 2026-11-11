import argparse
import asyncio

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository


async def create_admin(email: str, full_name: str, password: str) -> None:
    async with AsyncSessionLocal() as session:
        users = UserRepository(session)
        if await users.get_by_email(email.lower()) is not None:
            raise ValueError("Email already registered")
        await users.create(
            email=email.lower(),
            full_name=full_name,
            hashed_password=await hash_password(password),
            role=UserRole.ADMIN,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a TaskHub ADMIN user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(create_admin(args.email, args.full_name, args.password))


if __name__ == "__main__":
    main()
