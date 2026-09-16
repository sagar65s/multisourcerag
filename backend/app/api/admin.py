from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.security import AuthenticatedUser, admin_user
from app.services.admin_service import admin_overview, provider_overview
from app.services.audit_service import audit_event

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
async def overview(user: AuthenticatedUser = Depends(admin_user), settings: Settings = Depends(get_settings)) -> dict:
    await audit_event(user.uid, "admin_overview_view", resource_type="admin")
    return await admin_overview(settings)


@router.get("/providers")
async def providers(user: AuthenticatedUser = Depends(admin_user), settings: Settings = Depends(get_settings)) -> dict:
    await audit_event(user.uid, "admin_provider_view", resource_type="provider")
    return await provider_overview(settings)
