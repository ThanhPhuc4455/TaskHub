import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.cache import CACHE_BACKEND_ERRORS, create_redis_client
from app.core.config import settings
from app.core.constants import (
    APP_ERROR_CODE,
    HTTP_ERROR_CODE,
    INTERNAL_SERVER_ERROR_CODE,
    INTERNAL_SERVER_ERROR_MESSAGE,
    REFRESH_TOKEN_CLEANUP_INTERVAL_SECONDS,
    VALIDATION_ERROR_CODE,
)
from app.core.database import AsyncSessionLocal, engine
from app.core.exceptions import AppException
from app.core.middleware import RequestLoggingMiddleware
from app.repositories.refresh_token_repository import RefreshTokenRepository

logger = logging.getLogger(__name__)


async def _cleanup_refresh_tokens_periodically() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await RefreshTokenRepository(session).delete_expired_or_revoked()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Refresh-token cleanup failed")
        await asyncio.sleep(REFRESH_TOKEN_CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis_client = create_redis_client()
    app.state.redis_client = redis_client
    try:
        try:
            await redis_client.ping()
        except CACHE_BACKEND_ERRORS:
            logger.warning(
                "Redis unavailable during startup; cache will fall back to DB", exc_info=True
            )
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))  # fail-fast nếu không nối được DB
        cleanup_task = asyncio.create_task(_cleanup_refresh_tokens_periodically())
        try:
            yield
        finally:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task
    finally:
        await redis_client.aclose()
        with suppress(AttributeError):
            del app.state.redis_client
        await engine.dispose()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)


def _request_id(request: Request) -> str:
    return str(request.scope.get("state", {}).get("request_id", "-"))


def _error_content(detail: object, code: str, request: Request) -> dict[str, object]:
    return {"detail": detail, "code": code, "request_id": _request_id(request)}


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_content(str(exc), APP_ERROR_CODE, request),
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_content(exc.detail, HTTP_ERROR_CODE, request),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_error_content(jsonable_encoder(exc.errors()), VALIDATION_ERROR_CODE, request),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application exception request_id=%s", _request_id(request))
    return JSONResponse(
        status_code=500,
        content=_error_content(INTERNAL_SERVER_ERROR_MESSAGE, INTERNAL_SERVER_ERROR_CODE, request),
    )


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
