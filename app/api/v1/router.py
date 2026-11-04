from fastapi import APIRouter

from app.api.v1.endpoints import workspaces

api_router = APIRouter()
api_router.include_router(workspaces.router)
