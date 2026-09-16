import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.security import AuthenticatedUser, current_user
from app.schemas.account import AccountDeleteRequest, AccountView, UserSettingsUpdate, UserSettingsView
from app.services.account_profile_service import get_account_profile, sync_account_session
from app.services.user_settings_service import get_user_settings, update_user_settings
from app.services.account_service import delete_account_data
from app.core.rate_limit import limiter

router = APIRouter(prefix="/account", tags=["account privacy"])

def has_recent_auth(auth_time: int, now: int | None = None) -> bool:
    return auth_time > 0 and (now if now is not None else int(time.time())) - auth_time <= 600


@router.post("/session", response_model=AccountView)
@limiter.limit("30/minute")
async def synchronize_session(request: Request, response: Response, user: AuthenticatedUser = Depends(current_user)) -> AccountView:
    return await sync_account_session(user)


@router.get("", response_model=AccountView)
async def account_profile(user: AuthenticatedUser = Depends(current_user)) -> AccountView:
    return await get_account_profile(user)


@router.get("/settings", response_model=UserSettingsView)
async def account_settings(user: AuthenticatedUser = Depends(current_user)) -> UserSettingsView:
    return await get_user_settings(user.uid)


@router.patch("/settings", response_model=UserSettingsView)
async def change_account_settings(payload: UserSettingsUpdate, user: AuthenticatedUser = Depends(current_user)) -> UserSettingsView:
    return await update_user_settings(user.uid, payload)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/hour")
async def delete_account(request: Request, response: Response, payload: AccountDeleteRequest, user: AuthenticatedUser = Depends(current_user), settings: Settings = Depends(get_settings)) -> Response:
    if not has_recent_auth(user.auth_time):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please sign in again before permanently deleting your account")
    await delete_account_data(user.uid, settings)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
