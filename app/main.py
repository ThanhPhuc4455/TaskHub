import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.constants import REFRESH_TOKEN_CLEANUP_INTERVAL_SECONDS
from app.core.database import AsyncSessionLocal, engine
from app.core.exceptions import AppException, AuthenticationError
from app.repositories.refresh_token_repository import RefreshTokenRepository

logger = logging.getLogger(__name__)


async def _cleanup_refresh_tokens_periodically() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await RefreshTokenRepository(session).delete_expired()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Refresh-token cleanup failed")
        await asyncio.sleep(REFRESH_TOKEN_CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))  # fail-fast nếu không nối được DB
    cleanup_task = asyncio.create_task(_cleanup_refresh_tokens_periodically())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        await engine.dispose()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
        headers=headers,
    )


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
