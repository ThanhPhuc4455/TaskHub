from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))  # fail-fast nếu không nối được DB
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(AuthenticationError)
async def authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(BadRequestError)
async def bad_request_handler(request: Request, exc: BadRequestError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
