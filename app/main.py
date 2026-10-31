from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import NotFoundError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    print("Startup")  # ngày 2: mở kết nối DB
    yield
    print("Shutdown")  # ngày 2: đóng kết nối DB


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)