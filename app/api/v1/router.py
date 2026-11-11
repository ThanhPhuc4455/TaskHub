from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.endpoints import auth, members, projects, users, workspaces

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(members.router, dependencies=[Depends(get_current_user)])
api_router.include_router(workspaces.router, dependencies=[Depends(get_current_user)])
api_router.include_router(projects.router, dependencies=[Depends(get_current_user)])
