from fastapi import APIRouter, Depends

from app.core.security import AuthenticatedUser, current_user
from app.services.dashboard_service import dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def overview(user: AuthenticatedUser = Depends(current_user)) -> dict:
    return await dashboard_overview(user.uid)
